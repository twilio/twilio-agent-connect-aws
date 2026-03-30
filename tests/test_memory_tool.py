"""Tests for Strands memory tool."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from tac_aws.tools.strands import create_memory_tool

if TYPE_CHECKING:
    from tac.context.memory import MemoryClient


@pytest.fixture
def mock_memory_client() -> MagicMock:
    """Create a mock MemoryClient."""
    client = MagicMock()
    client.retrieve_memory = AsyncMock()
    return client


@pytest.fixture
def mock_memory_response() -> MagicMock:
    """Create a mock memory response."""
    response = MagicMock()
    response.model_dump = MagicMock(
        return_value={
            "profile_id": "prof_123",
            "observations": [{"text": "User prefers Python"}],
            "summaries": [{"text": "Developer"}],
            "sessions": [],
        }
    )
    return response


class TestMemoryTool:
    """Test suite for Strands memory tool."""

    @pytest.mark.asyncio
    async def test_create_memory_tool_returns_callable(
        self, mock_memory_client: MagicMock
    ) -> None:
        """Test that create_memory_tool returns a callable tool."""
        tool = create_memory_tool(mock_memory_client)

        # Verify tool is callable
        assert callable(tool)

        # Verify tool has expected attributes (Strands @tool decorator adds these)
        assert hasattr(tool, "__name__")
        assert tool.__name__ == "retrieve_twilio_memory"

    @pytest.mark.asyncio
    async def test_memory_tool_basic_retrieval(
        self, mock_memory_client: MagicMock, mock_memory_response: MagicMock
    ) -> None:
        """Test basic memory retrieval without optional parameters."""
        mock_memory_client.retrieve_memory.return_value = mock_memory_response

        tool = create_memory_tool(mock_memory_client)
        result = await tool(profile_id="prof_123")

        # Verify client was called correctly
        mock_memory_client.retrieve_memory.assert_called_once_with(
            profile_id="prof_123",
            conversation_id=None,
            query=None,
        )

        # Verify response was converted to dict
        assert isinstance(result, dict)
        assert result["profile_id"] == "prof_123"
        assert "observations" in result

    @pytest.mark.asyncio
    async def test_memory_tool_with_conversation_id(
        self, mock_memory_client: MagicMock, mock_memory_response: MagicMock
    ) -> None:
        """Test memory retrieval with conversation_id filter."""
        mock_memory_client.retrieve_memory.return_value = mock_memory_response

        tool = create_memory_tool(mock_memory_client)
        result = await tool(profile_id="prof_123", conversation_id="conv_456")

        # Verify client was called with conversation_id
        mock_memory_client.retrieve_memory.assert_called_once_with(
            profile_id="prof_123",
            conversation_id="conv_456",
            query=None,
        )

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_memory_tool_with_query(
        self, mock_memory_client: MagicMock, mock_memory_response: MagicMock
    ) -> None:
        """Test memory retrieval with semantic search query."""
        mock_memory_client.retrieve_memory.return_value = mock_memory_response

        tool = create_memory_tool(mock_memory_client)
        result = await tool(
            profile_id="prof_123",
            query="Tell me about the user's programming preferences",
        )

        # Verify client was called with query
        mock_memory_client.retrieve_memory.assert_called_once_with(
            profile_id="prof_123",
            conversation_id=None,
            query="Tell me about the user's programming preferences",
        )

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_memory_tool_with_all_parameters(
        self, mock_memory_client: MagicMock, mock_memory_response: MagicMock
    ) -> None:
        """Test memory retrieval with all optional parameters."""
        mock_memory_client.retrieve_memory.return_value = mock_memory_response

        tool = create_memory_tool(mock_memory_client)
        result = await tool(
            profile_id="prof_123",
            conversation_id="conv_456",
            query="programming preferences",
        )

        # Verify client was called with all parameters
        mock_memory_client.retrieve_memory.assert_called_once_with(
            profile_id="prof_123",
            conversation_id="conv_456",
            query="programming preferences",
        )

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_memory_tool_error_handling(self, mock_memory_client: MagicMock) -> None:
        """Test that tool properly handles and wraps errors."""
        # Make client raise an error
        mock_memory_client.retrieve_memory.side_effect = Exception("Network error")

        tool = create_memory_tool(mock_memory_client)

        # Verify tool raises ValueError with proper message
        with pytest.raises(ValueError) as exc_info:
            await tool(profile_id="prof_123")

        assert "Failed to retrieve memory" in str(exc_info.value)
        assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_memory_tool_model_dump_called_correctly(
        self, mock_memory_client: MagicMock, mock_memory_response: MagicMock
    ) -> None:
        """Test that model_dump is called with correct parameters."""
        mock_memory_client.retrieve_memory.return_value = mock_memory_response

        tool = create_memory_tool(mock_memory_client)
        await tool(profile_id="prof_123")

        # Verify model_dump was called with correct flags
        mock_memory_response.model_dump.assert_called_once_with(
            by_alias=True, exclude_none=True
        )

    @pytest.mark.asyncio
    async def test_multiple_memory_clients(
        self, mock_memory_response: MagicMock
    ) -> None:
        """Test that different tools use their respective memory clients."""
        client1 = MagicMock()
        client1.retrieve_memory = AsyncMock(return_value=mock_memory_response)

        client2 = MagicMock()
        client2.retrieve_memory = AsyncMock(return_value=mock_memory_response)

        tool1 = create_memory_tool(client1)
        tool2 = create_memory_tool(client2)

        # Call each tool
        await tool1(profile_id="prof_1")
        await tool2(profile_id="prof_2")

        # Verify each client was called with its respective profile
        client1.retrieve_memory.assert_called_once_with(
            profile_id="prof_1",
            conversation_id=None,
            query=None,
        )
        client2.retrieve_memory.assert_called_once_with(
            profile_id="prof_2",
            conversation_id=None,
            query=None,
        )
