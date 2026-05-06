"""Tests for BedrockConnector."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tac_aws.connectors import BedrockConnector

if TYPE_CHECKING:
    from mypy_boto3_bedrock_agent_runtime.type_defs import InvokeAgentResponseTypeDef


class TestBedrockConnector:
    """Test suite for BedrockConnector."""

    def test_initialization(self, mock_tac: MagicMock) -> None:
        """Test connector initialization with invoke function."""
        mock_invoke_fn = MagicMock()

        with (
            patch("tac_aws.connectors.bedrock_connector.VoiceChannel"),
            patch("tac_aws.connectors.bedrock_connector.SMSChannel"),
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
        sms_config = {"memory_mode": "always"}
        voice_config = {"memory_mode": "never"}

        with (
            patch("tac_aws.connectors.bedrock_connector.VoiceChannel") as mock_voice,
            patch("tac_aws.connectors.bedrock_connector.SMSChannel") as mock_sms,
        ):
            connector = BedrockConnector(
                tac=mock_tac,
                invoke_fn=mock_invoke_fn,
                sms_config=sms_config,
                voice_config=voice_config,
            )

            mock_voice.assert_called_once_with(tac=mock_tac, config=voice_config)
            mock_sms.assert_called_once_with(tac=mock_tac, config=sms_config)
            assert connector is not None

    def test_initialization_with_config(self, mock_tac: MagicMock) -> None:
        """Test connector initialization with config-based approach."""
        mock_client = MagicMock()
        config = {
            "agentId": "AGENT123",
            "agentAliasId": "TSTALIASID",
            "sessionId": "",
        }

        with (
            patch("tac_aws.connectors.bedrock_connector.VoiceChannel"),
            patch("tac_aws.connectors.bedrock_connector.SMSChannel"),
        ):
            connector = BedrockConnector(
                tac=mock_tac,
                bedrock_client=mock_client,
                config=config,
            )

            mock_tac.on_message_ready.assert_called_once()
            assert connector.tac == mock_tac
            assert connector.invoke_fn is not None

    def test_initialization_validation_both_patterns(self, mock_tac: MagicMock) -> None:
        """Test that providing both invoke_fn and config raises error."""
        mock_client = MagicMock()
        mock_invoke_fn = MagicMock()
        config = {"agentId": "AGENT123", "agentAliasId": "TSTALIASID", "sessionId": ""}

        with (
            patch("tac_aws.connectors.bedrock_connector.VoiceChannel"),
            patch("tac_aws.connectors.bedrock_connector.SMSChannel"),
        ):
            with pytest.raises(ValueError, match="Cannot use both invoke_fn and config"):
                BedrockConnector(
                    tac=mock_tac,
                    bedrock_client=mock_client,
                    config=config,
                    invoke_fn=mock_invoke_fn,
                )

    def test_initialization_validation_neither_pattern(self, mock_tac: MagicMock) -> None:
        """Test that providing neither invoke_fn nor config raises error."""
        with (
            patch("tac_aws.connectors.bedrock_connector.VoiceChannel"),
            patch("tac_aws.connectors.bedrock_connector.SMSChannel"),
        ):
            with pytest.raises(ValueError, match="Must provide either invoke_fn OR"):
                BedrockConnector(tac=mock_tac)

    @pytest.mark.asyncio
    async def test_handle_message_with_config_based_invoke(
        self,
        mock_tac: MagicMock,
        mock_conversation_session: MagicMock,
    ) -> None:
        """Test that config-based approach correctly invokes agent."""
        mock_client = MagicMock()
        mock_response: InvokeAgentResponseTypeDef = {
            "completion": [
                {"chunk": {"bytes": b"Hello "}},
                {"chunk": {"bytes": b"world!"}},
            ],
            "contentType": "text/plain",
            "sessionId": "session123",
            "ResponseMetadata": {},
        }
        mock_client.invoke_agent.return_value = mock_response

        config = {
            "agentId": "AGENT123",
            "agentAliasId": "TSTALIASID",
            "sessionId": "",
            "enableTrace": False,
        }

        with (
            patch("tac_aws.connectors.bedrock_connector.VoiceChannel") as mock_voice_channel,
            patch("tac_aws.connectors.bedrock_connector.SMSChannel"),
        ):
            mock_voice = AsyncMock()
            mock_voice_channel.return_value = mock_voice

            connector = BedrockConnector(
                tac=mock_tac,
                bedrock_client=mock_client,
                config=config,
            )

            mock_conversation_session.channel = "voice"
            mock_conversation_session.conversation_id = "conv123"

            await connector._handle_message(
                user_message="Test message",
                context=mock_conversation_session,
                memory_response=None,
            )

            # Verify invoke_agent was called with merged config
            mock_client.invoke_agent.assert_called_once()
            call_kwargs = mock_client.invoke_agent.call_args[1]
            assert call_kwargs["agentId"] == "AGENT123"
            assert call_kwargs["agentAliasId"] == "TSTALIASID"
            assert call_kwargs["sessionId"] == "conv123"  # Auto-injected
            assert call_kwargs["inputText"] == "Test message"  # Auto-injected
            assert call_kwargs["enableTrace"] is False

            # Verify response was sent to voice channel (buffered string)
            assert mock_voice.send_response.call_count == 1
            call_args = mock_voice.send_response.call_args
            assert call_args[0][0] == "conv123"  # conversation_id
            assert isinstance(call_args[0][1], str)  # response is buffered string
            assert call_args[1]["role"] == "assistant"

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

        with (
            patch("tac_aws.connectors.bedrock_connector.VoiceChannel"),
            patch("tac_aws.connectors.bedrock_connector.SMSChannel"),
            patch("tac_aws.connectors.bedrock_connector.MemoryPromptBuilder"),
        ):
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

            # Verify response was sent to voice channel (buffered string)
            assert connector.voice.send_response.call_count == 1
            call_args = connector.voice.send_response.call_args
            assert call_args[0][0] == "test_conv_123"  # conversation_id
            assert isinstance(call_args[0][1], str)  # response is buffered string
            assert call_args[1]["role"] == "assistant"

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

        with (
            patch("tac_aws.connectors.bedrock_connector.VoiceChannel"),
            patch("tac_aws.connectors.bedrock_connector.SMSChannel"),
            patch(
                "tac_aws.connectors.bedrock_connector.MemoryPromptBuilder"
            ) as mock_memory_builder,
        ):
            mock_memory_builder.build = MagicMock(return_value="Memory context")

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

            mock_memory_builder.build.assert_called_once_with(
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

        with (
            patch("tac_aws.connectors.bedrock_connector.VoiceChannel"),
            patch("tac_aws.connectors.bedrock_connector.SMSChannel"),
            patch("tac_aws.connectors.bedrock_connector.MemoryPromptBuilder"),
        ):
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

        with (
            patch("tac_aws.connectors.bedrock_connector.VoiceChannel"),
            patch("tac_aws.connectors.bedrock_connector.SMSChannel"),
            patch("tac_aws.connectors.bedrock_connector.MemoryPromptBuilder"),
        ):
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

        with (
            patch("tac_aws.connectors.bedrock_connector.VoiceChannel"),
            patch("tac_aws.connectors.bedrock_connector.SMSChannel"),
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

        with (
            patch("tac_aws.connectors.bedrock_connector.VoiceChannel"),
            patch("tac_aws.connectors.bedrock_connector.SMSChannel"),
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
