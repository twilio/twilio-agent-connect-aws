"""Strands tool for Twilio Memory retrieval using TAC MemoryClient."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tac.context.memory import MemoryClient


def create_memory_tool(memory_client: MemoryClient) -> Any:
    """
    Create a Strands tool for retrieving Twilio Memory data.

    This tool enables Strands agents to retrieve conversation memories, including
    observations, summaries, and session history from Twilio Memory Service.

    Uses the Strands @tool decorator pattern for automatic metadata extraction
    and proper tool registration.

    Args:
        memory_client: Configured TAC MemoryClient instance

    Returns:
        DecoratedFunctionTool configured for memory retrieval

    Example:
        ```python
        from tac import TAC, TACConfig
        from tac_aws.tools.strands import create_memory_tool

        tac = TAC(config=TACConfig.from_env())
        memory_tool = create_memory_tool(tac.memora_client)

        # Add to Strands agent
        agent = Agent(
            model="amazon.nova-pro-v1:0",
            system_prompt="You are helpful.",
            tools=[memory_tool],
        )
        ```
    """
    from strands import tool

    @tool
    async def retrieve_twilio_memory(
        profile_id: str,
        conversation_id: str | None = None,
        query: str | None = None,
    ) -> dict:
        """
        Retrieves conversation memories from Twilio Memory Service.

        Returns observations, summaries, and session history for a given profile.
        Supports semantic search with optional query parameter.

        Args:
            profile_id: Profile ID in Twilio Type ID (TTID) format (e.g., prof_*)
            conversation_id: Optional conversation ID in TTID format (e.g., conv_*) to filter memories
            query: Optional semantic search query for finding relevant memories (max 1024 characters)

        Returns:
            Dictionary containing memory data with observations, summaries, sessions, and metadata
        """
        try:
            # Call TAC MemoryClient
            memory_response = await memory_client.retrieve_memory(
                profile_id=profile_id,
                conversation_id=conversation_id,
                query=query,
            )

            # Convert response to dict and return (Strands will handle serialization)
            return memory_response.model_dump(by_alias=True, exclude_none=True)

        except Exception as e:
            # Raise exception - Strands decorator will handle error formatting
            raise ValueError(f"Failed to retrieve memory: {str(e)}") from e

    return retrieve_twilio_memory
