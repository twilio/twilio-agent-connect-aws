"""Tests for BedrockConnector."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tac_aws.connectors import BedrockConnector

if TYPE_CHECKING:
    from mypy_boto3_bedrock_agent_runtime.type_defs import InvokeAgentResponseTypeDef
    from tac.models.session import ConversationSession


class TestBedrockConnector:
    """Test suite for BedrockConnector."""

    def test_initialization(self, mock_tac: MagicMock) -> None:
        """Test connector initialization with invoke function."""
        mock_invoke_fn = MagicMock()

        with patch("tac_aws.connectors.bedrock_connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_connector.SMSChannel"
        ):
            connector = BedrockConnector(
                tac=mock_tac,
                invoke_fn=mock_invoke_fn,
            )

            mock_tac.on_message_ready.assert_called_once()
            assert connector.tac == mock_tac
            assert connector.invoke_fn == mock_invoke_fn

    def test_initialization_with_channel_configs(self, mock_tac: MagicMock) -> None:
        """Test connector initialization with custom channel configs."""
        mock_invoke_fn = MagicMock()
        sms_config = {"auto_retrieve_memory": True}
        voice_config = {"auto_retrieve_memory": False}

        with patch("tac_aws.connectors.bedrock_connector.VoiceChannel") as MockVoice, patch(
            "tac_aws.connectors.bedrock_connector.SMSChannel"
        ) as MockSMS:
            connector = BedrockConnector(
                tac=mock_tac,
                invoke_fn=mock_invoke_fn,
                sms_config=sms_config,
                voice_config=voice_config,
            )

            MockVoice.assert_called_once_with(tac=mock_tac, config=voice_config)
            MockSMS.assert_called_once_with(tac=mock_tac, config=sms_config)
            assert connector is not None

    @pytest.mark.asyncio
    async def test_handle_message_calls_invoke_fn(
        self,
        mock_tac: MagicMock,
        mock_conversation_session: MagicMock,
    ) -> None:
        """Test that handling a message calls user's invoke function."""
        mock_invoke_fn = MagicMock()
        mock_response: InvokeAgentResponseTypeDef = {
            "completion": [
                {"chunk": {"bytes": b"Test response"}},
            ],
            "ResponseMetadata": {},
        }
        mock_invoke_fn.return_value = mock_response

        with patch("tac_aws.connectors.bedrock_connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_connector.SMSChannel"
        ), patch("tac_aws.connectors.bedrock_connector.MemoryPromptBuilder"):
            connector = BedrockConnector(
                tac=mock_tac,
                invoke_fn=mock_invoke_fn,
            )
            connector.voice.send_response = AsyncMock()

            await connector._handle_message(
                user_message="Hello",
                context=mock_conversation_session,
                memory_response=None,
            )

            mock_invoke_fn.assert_called_once_with(mock_conversation_session, "Hello", None)
            connector.voice.send_response.assert_called_once_with(
                "test_conv_123", "Test response", role="assistant"
            )

    @pytest.mark.asyncio
    async def test_handle_message_with_memory_injection(
        self,
        mock_tac: MagicMock,
        mock_conversation_session: MagicMock,
        mock_memory_response: MagicMock,
    ) -> None:
        """Test that memory context is passed to invoke function."""
        mock_invoke_fn = MagicMock()
        mock_response: InvokeAgentResponseTypeDef = {
            "completion": [
                {"chunk": {"bytes": b"Response"}},
            ],
            "ResponseMetadata": {},
        }
        mock_invoke_fn.return_value = mock_response

        with patch("tac_aws.connectors.bedrock_connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_connector.SMSChannel"
        ), patch("tac_aws.connectors.bedrock_connector.MemoryPromptBuilder") as MockMemoryBuilder:
            MockMemoryBuilder.build = MagicMock(return_value="Memory context")

            connector = BedrockConnector(
                tac=mock_tac,
                invoke_fn=mock_invoke_fn,
            )
            connector.voice.send_response = AsyncMock()

            await connector._handle_message(
                user_message="Hello",
                context=mock_conversation_session,
                memory_response=mock_memory_response,
            )

            MockMemoryBuilder.build.assert_called_once_with(
                mock_memory_response, mock_conversation_session
            )
            mock_invoke_fn.assert_called_once_with(
                mock_conversation_session, "Hello", "Memory context"
            )

    @pytest.mark.asyncio
    async def test_handle_message_routes_to_voice_channel(
        self,
        mock_tac: MagicMock,
        mock_conversation_session: MagicMock,
    ) -> None:
        """Test that responses are routed to voice channel."""
        mock_conversation_session.channel = "voice"
        mock_invoke_fn = MagicMock()
        mock_response: InvokeAgentResponseTypeDef = {
            "completion": [
                {"chunk": {"bytes": b"Voice response"}},
            ],
            "ResponseMetadata": {},
        }
        mock_invoke_fn.return_value = mock_response

        with patch("tac_aws.connectors.bedrock_connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_connector.SMSChannel"
        ), patch("tac_aws.connectors.bedrock_connector.MemoryPromptBuilder"):
            connector = BedrockConnector(
                tac=mock_tac,
                invoke_fn=mock_invoke_fn,
            )
            connector.voice.send_response = AsyncMock()
            connector.sms.send_response = AsyncMock()

            await connector._handle_message(
                user_message="Hello",
                context=mock_conversation_session,
                memory_response=None,
            )

            connector.voice.send_response.assert_called_once()
            connector.sms.send_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_error_handling(
        self,
        mock_tac: MagicMock,
        mock_conversation_session: MagicMock,
    ) -> None:
        """Test error handling during message processing."""
        mock_invoke_fn = MagicMock(side_effect=Exception("Test error"))

        with patch("tac_aws.connectors.bedrock_connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_connector.SMSChannel"
        ), patch("tac_aws.connectors.bedrock_connector.MemoryPromptBuilder"):
            connector = BedrockConnector(
                tac=mock_tac,
                invoke_fn=mock_invoke_fn,
            )
            connector.voice.send_response = AsyncMock()

            await connector._handle_message(
                user_message="Hello",
                context=mock_conversation_session,
                memory_response=None,
            )

            connector.voice.send_response.assert_called_once()
            call_args = connector.voice.send_response.call_args
            assert "error" in call_args[0][1].lower()

    def test_parse_response_with_streaming_chunks(self, mock_tac: MagicMock) -> None:
        """Test parsing streaming response with multiple chunks."""
        mock_invoke_fn = MagicMock()

        with patch("tac_aws.connectors.bedrock_connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_connector.SMSChannel"
        ):
            connector = BedrockConnector(
                tac=mock_tac,
                invoke_fn=mock_invoke_fn,
            )

            mock_response: InvokeAgentResponseTypeDef = {
                "completion": [
                    {"chunk": {"bytes": b"Hello "}},
                    {"chunk": {"bytes": b"world"}},
                ],
                "ResponseMetadata": {},
            }

            result = connector._parse_response(mock_response)
            assert result == "Hello world"

    def test_parse_response_empty(self, mock_tac: MagicMock) -> None:
        """Test parsing empty response."""
        mock_invoke_fn = MagicMock()

        with patch("tac_aws.connectors.bedrock_connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_connector.SMSChannel"
        ):
            connector = BedrockConnector(
                tac=mock_tac,
                invoke_fn=mock_invoke_fn,
            )

            mock_response: InvokeAgentResponseTypeDef = {
                "completion": [],
                "ResponseMetadata": {},
            }

            result = connector._parse_response(mock_response)
            assert result == ""
