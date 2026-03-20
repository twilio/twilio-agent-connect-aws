"""Strands SDK adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from tac_aws.adapters.base import BaseAgentAdapter

if TYPE_CHECKING:
    from strands import Agent


class StrandsAdapter(BaseAgentAdapter):
    """Adapter for AWS Strands SDK."""

    def __init__(self, agent: Agent) -> None:
        """
        Initialize Strands adapter.

        Args:
            agent: Configured Strands Agent instance
        """
        self.agent = agent

    async def run_async(self, message: str, session_id: str, **kwargs: Any) -> str:
        """
        Run Strands agent asynchronously.

        Args:
            message: Input message or conversation history
            session_id: Session ID (not used - Strands manages state internally)
            **kwargs: Additional parameters passed to agent.invoke_async()

        Returns:
            Complete response text from agent
        """
        response = await self.agent.invoke_async(message, **kwargs)
        return str(response)

    async def stream_async(
        self, message: str, session_id: str, **kwargs: Any
    ) -> AsyncIterator[str]:
        """
        Run Strands agent with streaming.

        Args:
            message: Input message or conversation history
            session_id: Session ID (not used - Strands manages state internally)
            **kwargs: Additional parameters passed to agent.stream_async()

        Yields:
            Response text chunks
        """
        async for chunk in self.agent.stream_async(message, **kwargs):
            # Extract text from chunk based on Strands response format
            yield str(chunk)
