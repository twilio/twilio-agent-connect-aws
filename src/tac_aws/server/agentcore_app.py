"""
App adapter for TAC on AWS Bedrock AgentCore.

Integrates TAC channels with BedrockAgentCoreApp for serverless deployment.
Handles both HTTP (messaging channels) and WebSocket (Voice) protocols.
"""

import asyncio
import json
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from tac import TAC
from tac.core.logging import get_logger

if TYPE_CHECKING:
    from tac.channels.messaging import MessagingChannel
    from tac.channels.voice import VoiceChannel

logger = get_logger(__name__)


class TACAgentCoreWebSocketAdapter:
    """
    WebSocket wrapper that sends a welcome greeting after setup.

    Required for Twilio ConversationRelay with conversationConfiguration.
    Without an initial greeting, ConversationRelay won't activate speech detection.

    Pass `welcome_message=None` to skip it — do that when the TwiML already
    carries a `welcomeGreeting` (e.g. `AgentCoreLambdaProxy(twiml_options=...)`),
    otherwise the caller hears both greetings.
    """

    def __init__(
        self, ws: Any, welcome_message: str | None = "Hello! How can I assist you today?"
    ) -> None:
        self._ws = ws
        self._setup_received = False
        self._welcome_message = welcome_message

    async def receive_json(self) -> Any:
        data = await self._ws.receive_json()

        if self._welcome_message and not self._setup_received and data.get("type") == "setup":
            self._setup_received = True
            try:
                welcome_msg = {
                    "type": "text",
                    "token": self._welcome_message,
                    "last": True,
                }
                await self._ws.send_text(json.dumps(welcome_msg))
            except Exception as e:
                logger.error(f"Failed to send welcome greeting: {e}", exc_info=True)

        return data

    async def send_text(self, data: str) -> Any:
        return await self._ws.send_text(data)

    async def close(self) -> Any:
        return await self._ws.close()

    def __getattr__(self, name: str) -> Any:
        """Delegate all other attributes/methods to the underlying WebSocket.

        This allows the adapter to act as a transparent wrapper while only
        intercepting the specific methods we need to modify (receive_json).
        """
        return getattr(self._ws, name)


class TACAgentCoreApp:
    """
    App adapter for TAC on AWS Bedrock AgentCore.

    Integrates TAC channels with BedrockAgentCoreApp for serverless deployment.
    Handles both HTTP (messaging channels) and WebSocket (Voice) protocols.

    Args:
        tac: TAC instance
        voice_channel: Voice channel handling the ConversationRelay WebSocket
        messaging_channels: Messaging channels handling forwarded conversation
            webhooks — SMS, RCS, WhatsApp, Chat, in any combination. Pass
            `connector.channels.messaging` to wire up everything the connector
            enabled. A single channel is accepted for convenience. Each webhook
            is offered to every channel; a channel ignores the ones that aren't
            its own, exactly as `TACFastAPIServer` does.
        welcome_message: Greeting spoken once the ConversationRelay session is
            set up. Set to `None` when the TwiML already sets a
            `welcomeGreeting` — see `TACAgentCoreWebSocketAdapter`.
    """

    def __init__(
        self,
        tac: TAC,
        voice_channel: "VoiceChannel",
        messaging_channels: "Sequence[MessagingChannel] | MessagingChannel",
        welcome_message: str | None = "Hello! How can I assist you today?",
    ) -> None:
        self.tac = tac
        self.voice_channel = voice_channel
        self.messaging_channels: list[MessagingChannel] = (
            list(messaging_channels)
            if isinstance(messaging_channels, Sequence)
            else [messaging_channels]
        )
        self.welcome_message = welcome_message
        self.app = BedrockAgentCoreApp()

        # Register HTTP entrypoint for messaging channels
        # Note: Twilio webhook validation is performed in the Lambda proxy layer,
        # which validates the X-Twilio-Signature header before forwarding to AgentCore.
        # The Lambda then signs the request with AWS credentials when invoking AgentCore,
        # so we don't need to validate Twilio webhooks here.
        @self.app.entrypoint
        async def http_handler(payload: dict[str, Any]) -> dict[str, str]:
            try:
                webhook_data = json.loads(payload.get("webhook_data", "{}"))
                idempotency_token = payload.get("idempotency_token")

                await asyncio.gather(
                    *(
                        self._process_webhook(channel, webhook_data, idempotency_token)
                        for channel in self.messaging_channels
                    )
                )
                return {"status": "ok"}

            except Exception as e:
                logger.error(f"Error processing messaging webhook: {e}", exc_info=True)
                return {"status": "error", "message": "Internal server error"}

        # Register WebSocket entrypoint for Voice
        # Note: WebSocket connections use presigned URLs with AWS credentials generated
        # by the Lambda proxy layer. This ensures only authorized requests can connect.
        # Twilio Conversation Relay includes X-Twilio-Signature in the WebSocket handshake,
        # but AgentCore currently strips headers before passing to this handler.
        # Twilio webhook signature validation will be added once AgentCore supports custom
        # headers in WebSocket handlers. Until then, we rely on AWS credential validation
        # via presigned URLs.
        @self.app.websocket
        async def websocket_handler(websocket: Any, context: Any) -> None:
            try:
                wrapped_ws = TACAgentCoreWebSocketAdapter(websocket, self.welcome_message)
                await self.voice_channel.handle_websocket(wrapped_ws)

            except Exception as e:
                logger.error(f"Error in WebSocket handler: {e}", exc_info=True)
                try:
                    await websocket.close()
                except Exception:
                    pass

    @staticmethod
    async def _process_webhook(
        channel: "MessagingChannel",
        webhook_data: dict[str, Any],
        idempotency_token: str | None,
    ) -> None:
        """Hand one webhook to one channel; a failure there can't sink the others."""
        try:
            await channel.process_webhook(webhook_data, idempotency_token)
        except Exception as e:
            logger.error(
                "Error processing webhook in channel",
                channel=channel.get_channel_name(),
                error=str(e),
                exc_info=True,
            )

    def run(self) -> None:
        """Start the AgentCore app."""
        self.app.run()
