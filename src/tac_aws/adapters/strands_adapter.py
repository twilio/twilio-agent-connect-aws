"""Strands SDK adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING, Any

from tac_aws.adapters.base import BaseAgentAdapter

if TYPE_CHECKING:
    from strands import Agent


class StrandsAdapter(BaseAgentAdapter):
    """
    Adapter for AWS Strands SDK with per-conversation agent management.

    Strands agents have built-in conversation management via agent.messages.
    This adapter creates one agent instance per conversation to properly isolate
    conversation history across different conversations.

    Args:
        agent_factory: Factory function that creates a new Agent instance.
            Each conversation gets its own agent with independent conversation history.

    Example:
        ```python
        from strands import Agent

        # Create adapter with agent factory
        adapter = StrandsAdapter(
            agent_factory=lambda: Agent(
                model="amazon.nova-pro-v1:0",
                system_prompt="You are helpful.",
                tools=[memory_tool],
            )
        )
        ```
    """

    def __init__(self, agent_factory: Callable[[], Agent]) -> None:
        """
        Initialize Strands adapter with agent factory.

        Args:
            agent_factory: Factory function that creates a new Agent instance
        """
        self.agent_factory = agent_factory
        self.conversation_agents: dict[str, Agent] = {}  # One agent per conversation

    async def run_async(self, message: str, conversation_id: str, **kwargs: Any) -> str:
        """
        Run Strands agent asynchronously for a specific conversation.

        Strands agents maintain conversation history in agent.messages.
        This method gets or creates an agent for the conversation and invokes it
        with just the new message. Strands handles conversation history internally.

        Args:
            message: New user message (string only)
            conversation_id: Conversation ID for agent isolation
            **kwargs: Additional parameters passed to agent.invoke_async()

        Returns:
            Complete response text from agent
        """
        # Get or create agent for this conversation
        if conversation_id not in self.conversation_agents:
            self.conversation_agents[conversation_id] = self.agent_factory()

        # Invoke with new message - Strands manages history
        result = await self.conversation_agents[conversation_id].invoke_async(message, **kwargs)

        # AgentResult.__str__() handles text extraction automatically
        # Priority: interrupts > structured_output > concatenated text blocks
        return str(result)

    async def stream_async(
        self, message: str, conversation_id: str, **kwargs: Any
    ) -> AsyncIterator[str]:
        """
        Run Strands agent with streaming for a specific conversation.

        Args:
            message: New user message (string only)
            conversation_id: Conversation ID for agent isolation
            **kwargs: Additional parameters passed to agent.stream_async()

        Yields:
            Response text chunks
        """
        # Get or create agent for this conversation
        if conversation_id not in self.conversation_agents:
            self.conversation_agents[conversation_id] = self.agent_factory()

        # Stream from agent - Strands manages history
        async for chunk in self.conversation_agents[conversation_id].stream_async(message, **kwargs):
            # Extract text from chunk based on Strands response format
            yield str(chunk)

    def cleanup_conversation(self, conversation_id: str) -> None:
        """
        Clean up agent resources for a specific conversation.

        Should be called when a conversation ends to free resources.

        Args:
            conversation_id: Conversation ID to clean up
        """
        if conversation_id in self.conversation_agents:
            self.conversation_agents[conversation_id].cleanup()
            del self.conversation_agents[conversation_id]
