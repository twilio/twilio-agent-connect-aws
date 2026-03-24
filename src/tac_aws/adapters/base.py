"""Base adapter interface for agent runtimes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any


class BaseAgentAdapter(ABC):
    """
    Base adapter for agent runtimes.

    Provides a unified interface for different agent SDKs (Strands, Bedrock, Azure AI, etc.).
    Each adapter implements async/sync and streaming methods for agent invocation.
    """

    @abstractmethod
    async def run_async(self, message: str, conversation_id: str, **kwargs: Any) -> str:
        """
        Run agent asynchronously and return complete response.

        Args:
            message: Input message or prompt
            conversation_id: Session/conversation ID for state management
            **kwargs: Additional runtime-specific parameters

        Returns:
            Complete response text from agent
        """
        pass

    @abstractmethod
    def stream_async(
        self, message: str, conversation_id: str, **kwargs: Any
    ) -> AsyncIterator[str]:
        """
        Run agent asynchronously with streaming response.

        Note: This is an async generator, so implementations should use:
            async def stream_async(...) -> AsyncIterator[str]:
                yield "chunk"

        Args:
            message: Input message or prompt
            conversation_id: Session/conversation ID for state management
            **kwargs: Additional runtime-specific parameters

        Yields:
            Response text chunks as they become available
        """
        pass

    def run_sync(self, message: str, conversation_id: str, **kwargs: Any) -> str:
        """
        Run agent synchronously and return complete response.

        Args:
            message: Input message or prompt
            conversation_id: Session/conversation ID for state management
            **kwargs: Additional runtime-specific parameters

        Returns:
            Complete response text from agent

        Note:
            Default implementation raises NotImplementedError.
            Override if sync execution is needed.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support synchronous execution. "
            "Use run_async() instead."
        )
