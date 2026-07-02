"""Shared test fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_tac() -> MagicMock:
    """Create a mock TAC instance."""
    tac = MagicMock()
    tac.on_message_ready = MagicMock()
    return tac


@pytest.fixture
def mock_agent() -> MagicMock:
    """Create a mock Strands Agent instance."""
    agent = MagicMock(spec=["invoke_async", "stream_async", "cleanup"])
    agent.invoke_async = AsyncMock(return_value=MagicMock(__str__=lambda x: "Test response"))
    agent.stream_async = AsyncMock()
    agent.cleanup = MagicMock()
    return agent


@pytest.fixture
def mock_agent_factory(mock_agent: MagicMock) -> MagicMock:
    """Create a mock agent factory that returns a mock agent."""
    # Factory now takes ConversationSession as parameter
    factory = MagicMock(return_value=mock_agent)
    return factory


@pytest.fixture
def mock_conversation_session() -> MagicMock:
    """Create a mock ConversationSession."""
    session = MagicMock()
    session.conversation_id = "test_conv_123"
    session.channel = "voice"
    session.customer_id = "customer_123"
    return session


@pytest.fixture
def mock_memory_response() -> MagicMock:
    """Create a mock TACMemoryResponse."""
    memory = MagicMock()
    memory.facts = ["User prefers Python", "User is a developer"]
    return memory
