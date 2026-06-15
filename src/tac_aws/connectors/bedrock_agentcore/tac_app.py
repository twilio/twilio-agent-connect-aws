"""TAC adapter for AWS Bedrock AgentCore Runtime."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from tac import TAC
from tac.core.logging import get_logger

from .websocket_adapter import TACAgentCoreWebSocketAdapter

if TYPE_CHECKING:
    from tac.channels.sms import SMSChannel
    from tac.channels.voice import VoiceChannel

logger = get_logger(__name__)


class TACAgentCoreApp:
    """App adapter for TAC on AWS Bedrock AgentCore.

    Integrates TAC channels with BedrockAgentCoreApp for TAC deployment in AgentCore Runtime.
    Handles both HTTP (messaging) and WebSocket (voice) protocols.

    Example:
        tac = TAC(config=TACConfig.from_env())
        connector = BedrockAgentCoreConnector(tac=tac, ...)

        app = TACAgentCoreApp(
            tac=tac,
            voice_channel=connector.voice,
            sms_channel=connector.sms
        )
        app.run()
    """

    def __init__(self, tac: TAC, voice_channel: VoiceChannel, sms_channel: SMSChannel):
        """Initialize the AgentCore app with TAC channels.

        Args:
            tac: TAC instance
            voice_channel: Voice channel from connector
            sms_channel: SMS channel from connector
        """
        self.tac = tac
        self.voice_channel = voice_channel
        self.sms_channel = sms_channel
        self.app = BedrockAgentCoreApp()

        # Register HTTP entrypoint for messaging (SMS, WhatsApp)
        # Note: Twilio webhook signature validation is performed in the Lambda proxy
        # before invoking AgentCore, so we don't need to validate it here.
        @self.app.entrypoint
        async def http_handler(payload: dict[str, Any]) -> dict[str, Any]:
            try:
                webhook_data = json.loads(payload.get("webhook_data", "{}"))
                idempotency_token = payload.get("idempotency_token")

                await self.sms_channel.process_webhook(webhook_data, idempotency_token)
                return {"status": "ok"}

            except Exception as e:
                logger.error(f"Error processing SMS webhook: {e}", exc_info=True)
                return {"status": "error", "message": str(e)}

        # Register WebSocket entrypoint for Voice
        @self.app.websocket
        async def websocket_handler(websocket: Any, context: Any) -> None:
            # TODO: Add Twilio webhook signature validation
            # Conversation Relay includes X-Twilio-Signature header in the initial
            # WebSocket handshake request. We should validate this signature using the
            # Twilio auth token to ensure requests are genuinely from Twilio.
            # See: https://www.twilio.com/docs/voice/conversationrelay/onboarding
            # Note: Currently blocked because AgentCore strips headers from WebSocket requests.
            # This security enhancement should be implemented once AgentCore supports
            # passing handshake headers to the WebSocket handler.
            try:
                wrapped_ws = TACAgentCoreWebSocketAdapter(websocket)
                await self.voice_channel.handle_websocket(wrapped_ws)

            except Exception as e:
                logger.error(f"Error in WebSocket handler: {e}", exc_info=True)
                try:
                    await websocket.close()
                except Exception:
                    pass

    def run(self) -> None:
        """Start the AgentCore app."""
        self.app.run()
