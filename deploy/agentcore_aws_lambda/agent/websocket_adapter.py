"""
WebSocket adapter for TAC AgentCore integration.
"""
import json
from tac.core.logging import get_logger

logger = get_logger(__name__)


class TACAgentCoreWebSocketAdapter:
    """
    WebSocket adapter that sends a welcome greeting after setup.

    Required for Twilio ConversationRelay with conversationConfiguration.
    Without an initial greeting, ConversationRelay won't activate speech detection.
    """
    def __init__(self, ws, welcome_message: str = "Hello! How can I assist you today?"):
        self._ws = ws
        self._setup_received = False
        self._welcome_message = welcome_message

    async def receive_json(self):
        data = await self._ws.receive_json()

        if not self._setup_received and data.get('type') == 'setup':
            self._setup_received = True
            try:
                welcome_msg = {
                    "type": "text",
                    "token": self._welcome_message,
                    "last": True
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
        return getattr(self._ws, name)
