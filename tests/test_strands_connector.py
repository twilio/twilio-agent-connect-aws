"""Tests for StrandsConnector."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tac_aws.connectors import StrandsConnector

if TYPE_CHECKING:
    pass


class TestStrandsConnector:
    """Test suite for StrandsConnector."""

    def test_initialization(self, mock_tac: MagicMock, mock_agent_factory: MagicMock) -> None:
        """Test connector initialization."""
        with patch("tac_aws.connectors.strands_connector.VoiceChannel"), patch(
            "tac_aws.connectors.strands_connector.SMSChannel"
        ):
            connector = StrandsConnector(tac=mock_tac, agent_factory=mock_agent_factory)

            # Verify TAC callbacks registered
            mock_tac.on_message_ready.assert_called_once()
            mock_tac.on_conversation_ended.assert_called_once()

            # Verify initialization state
            assert connector.tac == mock_tac
            assert connector.agent_factory == mock_agent_factory
            assert connector.conversation_agents == {}
            assert connector.initialized_sessions == set()

    def test_initialization_with_channel_configs(
        self, mock_tac: MagicMock, mock_agent_factory: MagicMock
    ) -> None:
        """Test connector initialization with custom channel configs."""
        sms_config = {"memory_mode": "always"}
        voice_config = {"memory_mode": "never"}

        with patch("tac_aws.connectors.strands_connector.VoiceChannel") as mock_voice, patch(
            "tac_aws.connectors.strands_connector.SMSChannel"
        ) as mock_sms:
            connector = StrandsConnector(
                tac=mock_tac,
                agent_factory=mock_agent_factory,
                sms_config=sms_config,
                voice_config=voice_config,
            )

            # Verify channels created with configs
            mock_voice.assert_called_once_with(tac=mock_tac, config=voice_config)
            mock_sms.assert_called_once_with(tac=mock_tac, config=sms_config)
            assert connector is not None

    @pytest.mark.asyncio
    async def test_handle_message_creates_agent(
        self,
        mock_tac: MagicMock,
        mock_agent_factory: MagicMock,
        mock_agent: MagicMock,
        mock_conversation_session: MagicMock,
    ) -> None:
        """Test that handling a message creates an agent for new conversations."""
        with patch("tac_aws.connectors.strands_connector.VoiceChannel"), patch(
            "tac_aws.connectors.strands_connector.SMSChannel"
        ), patch("tac_aws.connectors.strands_connector.MemoryPromptBuilder"):
            connector = StrandsConnector(tac=mock_tac, agent_factory=mock_agent_factory)

            # Mock the voice channel send_response
            connector.voice.send_response = AsyncMock()

            # Call the handler directly
            await connector._handle_message(
                user_message="Hello",
                context=mock_conversation_session,
                memory_response=None,
            )

            # Verify agent factory was called with context
            mock_agent_factory.assert_called_once_with(mock_conversation_session)

            # Verify agent was stored
            assert "test_conv_123" in connector.conversation_agents
            assert connector.conversation_agents["test_conv_123"] == mock_agent

            # Verify agent was invoked
            mock_agent.invoke_async.assert_called_once_with("Hello")

    @pytest.mark.asyncio
    async def test_handle_message_reuses_agent(
        self,
        mock_tac: MagicMock,
        mock_agent_factory: MagicMock,
        mock_agent: MagicMock,
        mock_conversation_session: MagicMock,
    ) -> None:
        """Test that handling messages for the same conversation reuses the agent."""
        with patch("tac_aws.connectors.strands_connector.VoiceChannel"), patch(
            "tac_aws.connectors.strands_connector.SMSChannel"
        ), patch("tac_aws.connectors.strands_connector.MemoryPromptBuilder"):
            connector = StrandsConnector(tac=mock_tac, agent_factory=mock_agent_factory)

            # Mock the voice channel send_response
            connector.voice.send_response = AsyncMock()

            # First message
            await connector._handle_message(
                user_message="Hello",
                context=mock_conversation_session,
                memory_response=None,
            )

            # Second message (same conversation)
            await connector._handle_message(
                user_message="How are you?",
                context=mock_conversation_session,
                memory_response=None,
            )

            # Verify agent factory was only called once
            assert mock_agent_factory.call_count == 1

            # Verify agent was invoked twice
            assert mock_agent.invoke_async.call_count == 2

    @pytest.mark.asyncio
    async def test_handle_message_with_memory(
        self,
        mock_tac: MagicMock,
        mock_agent_factory: MagicMock,
        mock_agent: MagicMock,
        mock_conversation_session: MagicMock,
        mock_memory_response: MagicMock,
    ) -> None:
        """Test that memory context is injected for new sessions."""
        with patch("tac_aws.connectors.strands_connector.VoiceChannel"), patch(
            "tac_aws.connectors.strands_connector.SMSChannel"
        ), patch(
            "tac_aws.connectors.strands_connector.MemoryPromptBuilder"
        ) as mock_memory_builder:
            mock_memory_builder.build = MagicMock(return_value="Memory context")

            connector = StrandsConnector(tac=mock_tac, agent_factory=mock_agent_factory)
            connector.voice.send_response = AsyncMock()

            # First message with memory
            await connector._handle_message(
                user_message="Hello",
                context=mock_conversation_session,
                memory_response=mock_memory_response,
            )

            # Verify memory was built and injected
            mock_memory_builder.build.assert_called_once_with(
                mock_memory_response, mock_conversation_session
            )

            # Verify agent was invoked twice (memory + user message)
            assert mock_agent.invoke_async.call_count == 2
            mock_agent.invoke_async.assert_any_call("Memory context")
            mock_agent.invoke_async.assert_any_call("Hello")

            # Verify session was marked as initialized
            assert "test_conv_123" in connector.initialized_sessions

    @pytest.mark.asyncio
    async def test_handle_message_routes_to_voice_channel(
        self,
        mock_tac: MagicMock,
        mock_agent_factory: MagicMock,
        mock_agent: MagicMock,
        mock_conversation_session: MagicMock,
    ) -> None:
        """Test that responses are routed to voice channel."""
        mock_conversation_session.channel = "voice"

        with patch("tac_aws.connectors.strands_connector.VoiceChannel"), patch(
            "tac_aws.connectors.strands_connector.SMSChannel"
        ), patch("tac_aws.connectors.strands_connector.MemoryPromptBuilder"):
            connector = StrandsConnector(tac=mock_tac, agent_factory=mock_agent_factory)
            connector.voice.send_response = AsyncMock()
            connector.sms.send_response = AsyncMock()

            await connector._handle_message(
                user_message="Hello",
                context=mock_conversation_session,
                memory_response=None,
            )

            # Verify voice channel was used
            connector.voice.send_response.assert_called_once_with(
                "test_conv_123", "Test response", role="assistant"
            )

            # Verify SMS channel was not used
            connector.sms.send_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_routes_to_sms_channel(
        self,
        mock_tac: MagicMock,
        mock_agent_factory: MagicMock,
        mock_agent: MagicMock,
        mock_conversation_session: MagicMock,
    ) -> None:
        """Test that responses are routed to SMS channel."""
        mock_conversation_session.channel = "sms"

        with patch("tac_aws.connectors.strands_connector.VoiceChannel"), patch(
            "tac_aws.connectors.strands_connector.SMSChannel"
        ), patch("tac_aws.connectors.strands_connector.MemoryPromptBuilder"):
            connector = StrandsConnector(tac=mock_tac, agent_factory=mock_agent_factory)
            connector.voice.send_response = AsyncMock()
            connector.sms.send_response = AsyncMock()

            await connector._handle_message(
                user_message="Hello",
                context=mock_conversation_session,
                memory_response=None,
            )

            # Verify SMS channel was used
            connector.sms.send_response.assert_called_once_with(
                "test_conv_123", "Test response", role="assistant"
            )

            # Verify voice channel was not used
            connector.voice.send_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_error_handling(
        self,
        mock_tac: MagicMock,
        mock_agent_factory: MagicMock,
        mock_agent: MagicMock,
        mock_conversation_session: MagicMock,
    ) -> None:
        """Test error handling during message processing."""
        # Make agent raise an error
        mock_agent.invoke_async = AsyncMock(side_effect=Exception("Test error"))

        with patch("tac_aws.connectors.strands_connector.VoiceChannel"), patch(
            "tac_aws.connectors.strands_connector.SMSChannel"
        ), patch("tac_aws.connectors.strands_connector.MemoryPromptBuilder"):
            connector = StrandsConnector(tac=mock_tac, agent_factory=mock_agent_factory)
            connector.voice.send_response = AsyncMock()

            # Should not raise, should send error message
            await connector._handle_message(
                user_message="Hello",
                context=mock_conversation_session,
                memory_response=None,
            )

            # Verify error message was sent
            connector.voice.send_response.assert_called_once()
            call_args = connector.voice.send_response.call_args
            assert "error" in call_args[0][1].lower()

    @pytest.mark.asyncio
    async def test_agent_factory_receives_context(
        self,
        mock_tac: MagicMock,
        mock_agent_factory: MagicMock,
        mock_agent: MagicMock,
        mock_conversation_session: MagicMock,
    ) -> None:
        """Test that agent factory receives ConversationSession context."""
        with patch("tac_aws.connectors.strands_connector.VoiceChannel"), patch(
            "tac_aws.connectors.strands_connector.SMSChannel"
        ), patch("tac_aws.connectors.strands_connector.MemoryPromptBuilder"):
            connector = StrandsConnector(tac=mock_tac, agent_factory=mock_agent_factory)
            connector.voice.send_response = AsyncMock()

            # Call handler
            await connector._handle_message(
                user_message="Test",
                context=mock_conversation_session,
                memory_response=None,
            )

            # Verify factory was called with the conversation context
            mock_agent_factory.assert_called_once_with(mock_conversation_session)

            # Verify context attributes are accessible
            assert mock_conversation_session.conversation_id == "test_conv_123"
            assert mock_conversation_session.channel == "voice"
            assert mock_conversation_session.customer_id == "customer_123"

    def test_automatic_cleanup_on_conversation_ended(
        self,
        mock_tac: MagicMock,
        mock_agent_factory: MagicMock,
        mock_agent: MagicMock,
        mock_conversation_session: MagicMock,
    ) -> None:
        """Test that conversation ended callback triggers automatic cleanup."""
        with patch("tac_aws.connectors.strands_connector.VoiceChannel"), patch(
            "tac_aws.connectors.strands_connector.SMSChannel"
        ), patch("tac_aws.connectors.strands_connector.MemoryPromptBuilder"):
            connector = StrandsConnector(tac=mock_tac, agent_factory=mock_agent_factory)

            # Add an agent and session to cleanup
            connector.conversation_agents["test_conv_123"] = mock_agent
            connector.initialized_sessions.add("test_conv_123")

            # Get the registered callback
            conversation_ended_callback = mock_tac.on_conversation_ended.call_args[0][0]

            # Trigger the callback with conversation context
            conversation_ended_callback(mock_conversation_session)

            # Verify cleanup was called
            mock_agent.cleanup.assert_called_once()

            # Verify agent was removed
            assert "test_conv_123" not in connector.conversation_agents
            assert "test_conv_123" not in connector.initialized_sessions
