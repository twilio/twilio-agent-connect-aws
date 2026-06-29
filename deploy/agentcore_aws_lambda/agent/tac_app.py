"""
App adapter for TAC on AWS Bedrock AgentCore.

Integrates TAC channels with BedrockAgentCoreApp for serverless deployment.
Handles both HTTP (SMS) and WebSocket (Voice) protocols.
"""

import json

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from tac import TAC
from tac.core.logging import get_logger

logger = get_logger(__name__)


class TACAgentCoreWebSocketAdapter:
    """
    WebSocket wrapper that sends a welcome greeting after setup.

    Required for Twilio ConversationRelay with conversationConfiguration.
    Without an initial greeting, ConversationRelay won't activate speech detection.
    """

    def __init__(self, ws, welcome_message: str = "Hello! How can I assist you today?"):
        self._ws = ws
        self._setup_received = False
        self._welcome_message = welcome_message

    async def receive_json(self):
        data = await self._ws.receive_json()

        if not self._setup_received and data.get("type") == "setup":
            self._setup_received = True
            try:
                welcome_msg = {
                    "type": "text",
                    "token": self._welcome_message,
                    "last": True,
                }
                await self._ws.send_text(json.dumps(welcome_msg))
            except Exception as e:
                logger.error(f"Failed to send welcome greeting: {e}")

        return data

    async def send_text(self, data: str):
        return await self._ws.send_text(data)

    async def close(self):
        return await self._ws.close()

    def __getattr__(self, name):
        """Delegate all other attributes/methods to the underlying WebSocket.

        This allows the adapter to act as a transparent wrapper while only
        intercepting the specific methods we need to modify (receive_json).
        """
        return getattr(self._ws, name)


class TACAgentCoreApp:
    """
    App adapter for TAC on AWS Bedrock AgentCore.

    Integrates TAC channels with BedrockAgentCoreApp for serverless deployment.
    Handles both HTTP (SMS) and WebSocket (Voice) protocols.
    """

    def __init__(
        self,
        tac: TAC,
        voice_channel,
        sms_channel,
        welcome_message: str = "Hello! How can I assist you today?",
    ):
        self.tac = tac
        self.voice_channel = voice_channel
        self.sms_channel = sms_channel
        self.welcome_message = welcome_message
        self.app = BedrockAgentCoreApp()

        # Register HTTP entrypoint for SMS
        # Note: Twilio webhook validation is performed in the Lambda proxy layer,
        # which validates the X-Twilio-Signature header before forwarding to AgentCore.
        # The Lambda then signs the request with AWS credentials when invoking AgentCore,
        # so we don't need to validate Twilio webhooks here.
        @self.app.entrypoint
        async def http_handler(payload):
            try:
                webhook_data = json.loads(payload.get("webhook_data", "{}"))
                idempotency_token = payload.get("idempotency_token")

                await self.sms_channel.process_webhook(webhook_data, idempotency_token)
                return {"status": "ok"}

            except Exception as e:
                logger.error(f"Error processing SMS webhook: {e}", exc_info=True)
                return {"status": "error", "message": str(e)}

        # Register WebSocket entrypoint for Voice
        # Note: WebSocket connections use presigned URLs with AWS credentials generated
        # by the Lambda proxy layer. This ensures only authorized requests can connect.
        # Twilio Conversation Relay includes X-Twilio-Signature in the WebSocket handshake,
        # but AgentCore currently strips headers before passing to this handler.
        # Twilio webhook signature validation will be added once AgentCore supports custom
        # headers in WebSocket handlers. Until then, we rely on AWS credential validation
        # via presigned URLs.
        @self.app.websocket
        async def websocket_handler(websocket, context):
            try:
                wrapped_ws = TACAgentCoreWebSocketAdapter(websocket, self.welcome_message)
                await self.voice_channel.handle_websocket(wrapped_ws)

            except Exception as e:
                logger.error(f"Error in WebSocket handler: {e}", exc_info=True)
                try:
                    await websocket.close()
                except Exception:
                    pass

    def run(self):
        """Start the AgentCore app."""
        self.app.run()
