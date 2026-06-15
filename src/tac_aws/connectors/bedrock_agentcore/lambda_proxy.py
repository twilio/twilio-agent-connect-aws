"""Lambda proxy for Twilio webhooks with AWS Bedrock AgentCore integration."""

from __future__ import annotations

import base64
import json
import os
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs

import boto3
from bedrock_agentcore.runtime import AgentCoreRuntimeClient
from tac.channels.voice.twiml import generate_twiml
from tac.core.logging import get_logger

from .validation import TwilioSignatureValidator

if TYPE_CHECKING:
    from mypy_boto3_bedrock_agentcore.client import BedrockAgentCoreClient

logger = get_logger(__name__)


class TACAgentCoreLambdaProxy:
    """Lambda proxy for Twilio webhooks with AgentCore integration.

    Example:
        proxy = TACAgentCoreLambdaProxy(
            agentcore_runtime_arn=os.environ['AGENTCORE_RUNTIME_ARN'],
            twilio_auth_token=os.environ['TWILIO_AUTH_TOKEN'],
            conversation_configuration_id=os.environ['TWILIO_CONVERSATION_CONFIGURATION_ID']
        )
        lambda_handler = proxy.lambda_handler
    """

    def __init__(
        self,
        agentcore_runtime_arn: str,
        twilio_auth_token: str,
        conversation_configuration_id: str,
        agent_core_client: BedrockAgentCoreClient | None = None,
        agentcore_runtime_client: AgentCoreRuntimeClient | None = None,
    ):
        """Initialize the lambda proxy.

        Clients are created automatically if not provided, using AWS_REGION from environment
        (set automatically in Lambda).

        Args:
            agentcore_runtime_arn: ARN of the AgentCore runtime
            twilio_auth_token: Twilio auth token for signature validation
            conversation_configuration_id: Twilio conversation configuration ID
            agent_core_client: Optional boto3 bedrock-agentcore client
            agentcore_runtime_client: Optional AgentCoreRuntimeClient instance
        """
        self.agentcore_runtime_arn = agentcore_runtime_arn
        self.conversation_configuration_id = conversation_configuration_id
        self.signature_validator = TwilioSignatureValidator(twilio_auth_token)

        if agent_core_client is None or agentcore_runtime_client is None:
            aws_region = os.environ.get("AWS_REGION")
            if not aws_region:
                raise ValueError("AWS_REGION environment variable must be set")

        self.agent_core_client = agent_core_client or boto3.client(
            "bedrock-agentcore", region_name=aws_region
        )
        self.agentcore_runtime_client = agentcore_runtime_client or AgentCoreRuntimeClient(
            region=aws_region
        )

    def extract_call_sid(self, event: dict) -> str | None:
        """Extract CallSid from Lambda event (POST body or query string)."""
        body = event.get("body", "")
        if body:
            if event.get("isBase64Encoded"):
                body = base64.b64decode(body).decode("utf-8")
            params = parse_qs(body)
            call_sid: str | None = params.get("CallSid", [None])[0]
            if call_sid:
                return call_sid

        query_params = event.get("queryStringParameters") or {}
        call_sid_from_query = query_params.get("CallSid")
        return call_sid_from_query if isinstance(call_sid_from_query, str) else None

    def validate_signature(self, event: dict) -> bool:
        """Validate Twilio webhook signature."""
        return self.signature_validator.validate(event)

    def handle_voice_twiml(self, event: dict) -> dict[str, Any]:
        """Generate TwiML for voice calls using CallSid as session_id for sticky routing."""
        try:
            call_sid = self.extract_call_sid(event)
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

            twiml = generate_twiml(
                options={
                    "websocket_url": websocket_url,
                    "conversation_configuration": self.conversation_configuration_id,
                }
            )

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
                "body": json.dumps({"error": str(e)}),
            }

    def handle_conversation_webhook(self, event: dict) -> dict[str, Any]:
        """Forward conversation webhooks to AgentCore.

        Only processes COMMUNICATION_CREATED and CONVERSATION_UPDATED events.
        Uses conversation_id as runtimeSessionId for sticky routing.
        """
        try:
            body = event.get("body", "")
            headers = event.get("headers", {})

            webhook_data = json.loads(body)
            event_type = webhook_data.get("eventType")
            event_data = webhook_data.get("data", {})

            if event_type not in ("COMMUNICATION_CREATED", "CONVERSATION_UPDATED"):
                logger.debug(f"Ignoring event type: {event_type}")
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"success": True, "ignored": True}),
                }

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
                "body": json.dumps({"error": str(e)}),
            }

    def lambda_handler(self, event: dict, context: Any) -> dict[str, Any]:
        """Route requests to appropriate handlers."""
        if not self.validate_signature(event):
            return {
                "statusCode": 403,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Invalid webhook signature"}),
            }

        request_path = event.get("rawPath", event.get("path", "/"))

        if request_path.startswith("/twiml"):
            return self.handle_voice_twiml(event)
        elif request_path.startswith("/webhook"):
            return self.handle_conversation_webhook(event)
        else:
            return {"statusCode": 404, "body": json.dumps({"error": "Not found"})}
