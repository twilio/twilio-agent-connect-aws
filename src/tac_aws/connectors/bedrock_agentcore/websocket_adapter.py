"""WebSocket adapter for TAC AgentCore integration."""

from __future__ import annotations

import json
from typing import Any

from tac.core.logging import get_logger

logger = get_logger(__name__)


class TACAgentCoreWebSocketAdapter:
    """WebSocket adapter that sends a welcome greeting after setup.

    Required for Twilio ConversationRelay with conversationConfiguration.
    Without an initial greeting, ConversationRelay won't activate speech detection.
    """

    def __init__(self, ws: Any, welcome_message: str = "Hello! How can I assist you today?"):
        """Initialize the WebSocket adapter.

        Args:
            ws: The underlying WebSocket connection
            welcome_message: Optional welcome message to send after setup
        """
        self._ws = ws
        self._setup_received = False
        self._welcome_message = welcome_message

    async def accept(self) -> None:
        """Accept the WebSocket connection."""
        await self._ws.accept()

    async def receive_json(self) -> dict[str, Any]:
        """Receive JSON data from WebSocket and handle setup messages."""
        data: dict[str, Any] = await self._ws.receive_json()

        if not self._setup_received and data.get("type") == "setup":
            self._setup_received = True
            try:
                welcome_msg = {"type": "text", "token": self._welcome_message, "last": True}
                await self._ws.send_text(json.dumps(welcome_msg))
            except Exception as e:
                logger.error(f"Failed to send welcome greeting: {e}")

        return data

    async def send_text(self, data: str) -> None:
        """Send text data to WebSocket."""
        await self._ws.send_text(data)

    async def close(self) -> None:
        """Close the WebSocket connection."""
        await self._ws.close()

    def __getattr__(self, name: str) -> Any:
        """Proxy all other attributes to the underlying WebSocket."""
        return getattr(self._ws, name)
