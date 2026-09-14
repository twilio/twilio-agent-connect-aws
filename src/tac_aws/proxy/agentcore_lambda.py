"""
AgentCore Lambda Proxy - Reusable Lambda handler wrapper for TAC integration.

This module provides a proxy class that wraps Lambda handler logic for Twilio webhook
routing to AWS Bedrock AgentCore. Users provide the Twilio auth token, and the proxy
handles signature validation and webhook routing internally.

Example usage:
    from tac_aws.proxy import AgentCoreLambdaProxy

    # Fetch Twilio auth token from Secrets Manager
    twilio_auth_token = fetch_twilio_auth_token(
        secret_arn=os.environ["TWILIO_SECRET_ARN"]
    )

    # Create proxy
    proxy = AgentCoreLambdaProxy(
        agentcore_runtime_arn=os.environ["AGENTCORE_RUNTIME_ARN"],
        conversation_configuration_id=os.environ["TWILIO_CONVERSATION_CONFIGURATION_ID"],
        twilio_auth_token=twilio_auth_token,
    )

    # Expose handler
    lambda_handler = proxy.lambda_handler
"""

import asyncio
import base64
import binascii
import json
import os
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import parse_qs

import boto3
from bedrock_agentcore.runtime import AgentCoreRuntimeClient
from tac.channels.voice.twiml import generate_twiml
from tac.core.logging import get_logger
from tac.models.voice import TwiMLOptions, TwiMLRequest

from .validation import TwilioSignatureValidator

logger = get_logger(__name__)

InboundCallTwiMLHandler = Callable[[TwiMLRequest], TwiMLOptions | Awaitable[TwiMLOptions]]
"""Per-call TwiML customizer. Sync or async; see ``on_inbound_call_twiml``."""


class AgentCoreLambdaProxy:
    """Lambda proxy for routing Twilio webhooks to AWS Bedrock AgentCore.

    This proxy handles:

    - Signature validation for Twilio webhooks
    - Voice call routing (generates TwiML with presigned WebSocket URL)
    - Conversation webhook routing (forwards to AgentCore via HTTP)

    **TwiML customization**: the ConversationRelay TwiML is built from the same
    `TwiMLOptions` model the TAC voice channel uses, layered highest precedence
    first:

    1. The customizer registered via `on_inbound_call_twiml(...)` — per call.
    2. `twiml_options` — static, applied to every call.
    3. Proxy defaults — the presigned `websocket_url` and
       `conversation_configuration`.

    Only fields a layer explicitly sets override lower layers, so setting a
    greeting doesn't drop the presigned WebSocket URL.

    Attributes:
        agentcore_runtime_arn: ARN of the AgentCore runtime
        conversation_configuration_id: Twilio Conversation Configuration ID
        signature_validator: TwilioSignatureValidator instance
        aws_region: AWS region for clients
        twiml_options: Static TwiMLOptions applied to every inbound call

    Example:
        ```python
        from tac.models.voice import TwiMLOptions, TwiMLRequest
        from tac_aws.proxy import AgentCoreLambdaProxy

        proxy = AgentCoreLambdaProxy(
            agentcore_runtime_arn=RUNTIME_ARN,
            conversation_configuration_id=CONFIG_ID,
            twilio_auth_token=AUTH_TOKEN,
            # Applies to every call
            twiml_options=TwiMLOptions(
                welcome_greeting="Hi! How can I help?",
                voice="en-US-Journey-O",
                interruptible="speech",
            ),
        )


        # Per-call overrides
        def by_country(req: TwiMLRequest) -> TwiMLOptions:
            if req.caller_country == "MX":
                return TwiMLOptions(language="es-MX", welcome_greeting="¡Hola!")
            return TwiMLOptions()


        proxy.on_inbound_call_twiml(by_country)

        lambda_handler = proxy.lambda_handler
        ```
    """

    def __init__(
        self,
        agentcore_runtime_arn: str,
        conversation_configuration_id: str,
        twilio_auth_token: str,
        aws_region: str | None = None,
        twiml_options: TwiMLOptions | dict[str, Any] | None = None,
    ) -> None:
        """Initialize AgentCore Lambda proxy.

        Args:
            agentcore_runtime_arn: ARN of the AgentCore runtime
            conversation_configuration_id: Twilio Conversation Configuration ID
            twilio_auth_token: Twilio auth token for webhook signature validation
            aws_region: AWS region for boto3 clients (optional, auto-detected from
                AWS_REGION env var, boto3 session, or AWS config)
            twiml_options: Static `TwiMLOptions` (or dict) applied to every
                inbound call — welcome greeting, voice, language, interruption
                behavior, and so on. Per-call overrides go through
                `on_inbound_call_twiml`.

        Raises:
            ValueError: If AWS region cannot be determined
        """
        self.agentcore_runtime_arn = agentcore_runtime_arn
        self.conversation_configuration_id = conversation_configuration_id
        self.signature_validator = TwilioSignatureValidator(twilio_auth_token)
        self.twiml_options = (
            TwiMLOptions(**twiml_options) if isinstance(twiml_options, dict) else twiml_options
        )
        self._on_inbound_call_twiml: InboundCallTwiMLHandler | None = None

        # Resolve AWS region: explicit parameter > AWS_REGION env var > boto3 session
        self.aws_region = aws_region or os.environ.get("AWS_REGION") or boto3.Session().region_name

        if not self.aws_region:
            raise ValueError(
                "AWS region not found. Provide aws_region parameter or configure AWS region."
            )

        self.agent_core_client = boto3.client("bedrock-agentcore", region_name=self.aws_region)
        self.agentcore_runtime_client = AgentCoreRuntimeClient(region=self.aws_region)

    def on_inbound_call_twiml(self, callback: InboundCallTwiMLHandler) -> None:
        """Register a callback producing per-call TwiML overrides for inbound calls.

        Mirrors `VoiceChannel.on_inbound_call_twiml` in TAC core: the callback
        receives a `TwiMLRequest` parsed from the Twilio voice webhook form
        (From, To, CallSid, CallerCountry, …) and returns a `TwiMLOptions`.
        Only fields it explicitly sets override `twiml_options` and the proxy
        defaults; unset fields fall through.

        Both sync and async callbacks are accepted — an async one is run to
        completion on a fresh event loop, since the Lambda handler is sync.

        Example:
            ```python
            def by_country(req: TwiMLRequest) -> TwiMLOptions:
                if req.caller_country == "MX":
                    return TwiMLOptions(language="es-MX", welcome_greeting="¡Hola!")
                return TwiMLOptions()


            proxy.on_inbound_call_twiml(by_country)
            ```

        Args:
            callback: Function called with the inbound `TwiMLRequest`, returning
                `TwiMLOptions` overrides for that call.
        """
        self._on_inbound_call_twiml = callback

    def lambda_handler(self, event: dict[str, Any], context: Any) -> dict[str, Any]:
        """Route requests to appropriate handler.

        Args:
            event: Lambda event containing HTTP request data
            context: Lambda context object

        Returns:
            Dict containing statusCode, headers, and body
        """
        if not self.signature_validator.validate(event):
            return {
                "statusCode": 403,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Invalid webhook signature"}),
            }

        request_path = event.get("rawPath", "/")

        if request_path.startswith("/twiml"):
            return self._handle_voice_twiml(event)
        elif request_path.startswith("/webhook"):
            return self._handle_conversation_webhook(event)
        else:
            return {
                "statusCode": 404,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Not found"}),
            }

    def _handle_voice_twiml(self, event: dict[str, Any]) -> dict[str, Any]:
        """Handle voice call - generate TwiML.

        Uses CallSid as session_id for AgentCore routing to ensure the call is routed
        to a dedicated agent instance based on CallSid.

        Args:
            event: Lambda event containing Twilio voice webhook data

        Returns:
            Dict containing statusCode 200 with TwiML body, or error response
        """
        try:
            form = self._parse_form(event)
            twiml_request = TwiMLRequest.from_form(form)
            call_sid = twiml_request.call_sid
            if not call_sid:
                logger.warning("Missing CallSid in voice webhook request")
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Missing CallSid parameter"}),
                }

            websocket_url = self.agentcore_runtime_client.generate_presigned_url(
                runtime_arn=self.agentcore_runtime_arn, session_id=call_sid, expires=300
            )

            twiml = generate_twiml(options=self._build_twiml_options(websocket_url, twiml_request))

            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/xml"},
                "body": twiml,
            }

        except Exception as e:
            logger.error(f"Error generating TwiML: {str(e)}", exc_info=True)
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Internal server error"}),
            }

    def _build_twiml_options(self, websocket_url: str, twiml_request: TwiMLRequest) -> TwiMLOptions:
        """Layer TwiML options for one inbound call, lowest precedence first.

        Proxy defaults (presigned ``websocket_url`` + ``conversation_configuration``)
        → static ``twiml_options`` → the ``on_inbound_call_twiml`` customizer.
        Only fields a layer explicitly set (Pydantic's ``model_fields_set``)
        are applied, so a layer that says nothing about the WebSocket URL can't
        clobber the presigned one.
        """
        merged = TwiMLOptions(
            websocket_url=websocket_url,
            conversation_configuration=self.conversation_configuration_id,
        )
        for layer in (self.twiml_options, self._resolve_per_call_options(twiml_request)):
            if layer is None:
                continue
            for field in layer.model_fields_set:
                setattr(merged, field, getattr(layer, field))
        return merged

    def _resolve_per_call_options(self, twiml_request: TwiMLRequest) -> TwiMLOptions | None:
        """Run the registered customizer, awaiting it when it's async.

        Under the Lambda runtime the handler is sync with no loop running, so an
        async customizer gets its own loop via ``asyncio.run``. When the handler
        is instead driven from inside a running loop — async tests, a local ASGI
        runner — ``asyncio.run`` would raise, so the coroutine is completed on a
        worker thread with its own loop.
        """
        if self._on_inbound_call_twiml is None:
            return None
        result = self._on_inbound_call_twiml(twiml_request)
        if isinstance(result, TwiMLOptions):
            return result

        async def resolve() -> TwiMLOptions:
            return await result

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(resolve())

        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, resolve()).result()

    def _parse_form(self, event: dict[str, Any]) -> dict[str, str]:
        """Parse a form-encoded Lambda event body into a flat dict.

        Returns an empty dict for a missing body or one that fails to decode —
        callers treat absent fields (notably CallSid) as the error case.
        """
        body = event.get("body") or ""
        if not body:
            return {}
        if event.get("isBase64Encoded"):
            try:
                body = base64.b64decode(body).decode("utf-8")
            except (TypeError, binascii.Error, UnicodeDecodeError) as e:
                logger.warning(f"Failed to decode request body: {e}")
                return {}
        params: dict[str, list[str]] = parse_qs(body)
        return {key: values[0] for key, values in params.items() if values}

    def _normalize_headers(
        self, headers: dict[str, str] | dict[str, str | None] | None
    ) -> dict[str, str]:
        """Normalize HTTP headers to lowercase keys for case-insensitive lookup.

        HTTP headers are case-insensitive per RFC 7230.

        Args:
            headers: Raw headers dict from Lambda event (may be None, values may be None)

        Returns:
            Dict with lowercase keys for case-insensitive lookup (None values converted to "")
        """
        if headers is None:
            return {}
        return {k.lower(): (v or "") for k, v in headers.items()}

    def _handle_conversation_webhook(self, event: dict[str, Any]) -> dict[str, Any]:
        """Handle conversation webhook - forward to AgentCore.

        Conversation Orchestrator sends JSON webhooks. TAC processes only:
        - COMMUNICATION_CREATED: New message from customer (data.conversationId)
        - CONVERSATION_UPDATED: Conversation status changed (data.id)

        Other event types are ignored.

        Args:
            event: Lambda event containing Conversation Orchestrator webhook data

        Returns:
            Dict containing statusCode and success response
        """
        try:
            # Normalize body (handle None from body: null in event)
            body = event.get("body") or ""
            headers = self._normalize_headers(event.get("headers", {}))

            # Handle base64 encoding (Lambda may encode binary content)
            if event.get("isBase64Encoded"):
                try:
                    body = base64.b64decode(body).decode("utf-8")
                except (TypeError, binascii.Error, UnicodeDecodeError) as e:
                    logger.warning(f"Invalid base64 or UTF-8 encoding in request body: {e}")
                    return {
                        "statusCode": 400,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "Invalid request body encoding"}),
                    }

            # Parse JSON with explicit error handling
            try:
                webhook_data = json.loads(body)
            except (TypeError, json.JSONDecodeError) as e:
                logger.warning(f"Invalid JSON in webhook body: {e}")
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Invalid JSON payload"}),
                }

            event_type = webhook_data.get("eventType")
            event_data = webhook_data.get("data", {})

            if event_type not in ("COMMUNICATION_CREATED", "CONVERSATION_UPDATED"):
                logger.debug(f"Ignoring event type: {event_type}")
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"success": True, "ignored": True}),
                }

            # Extract conversation_id (location differs by event type)
            conversation_id = None
            if event_type == "COMMUNICATION_CREATED":
                conversation_id = event_data.get("conversationId")
            elif event_type == "CONVERSATION_UPDATED":
                conversation_id = event_data.get("id")

            if not conversation_id:
                logger.warning(f"Missing conversationId for event type {event_type}")
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Missing conversationId"}),
                }

            payload = json.dumps(
                {
                    "webhook_data": body,
                    "idempotency_token": headers.get("i-twilio-idempotency-token"),
                }
            ).encode()

            # Use conversation_id as runtimeSessionId for sticky routing to same microVM
            self.agent_core_client.invoke_agent_runtime(
                agentRuntimeArn=self.agentcore_runtime_arn,
                runtimeSessionId=conversation_id,
                payload=payload,
            )

            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"success": True}),
            }

        except Exception as e:
            logger.error(f"Error forwarding webhook to AgentCore: {str(e)}", exc_info=True)
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Internal server error"}),
            }
