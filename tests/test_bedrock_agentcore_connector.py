"""Tests for BedrockAgentCoreConnector."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tac_aws.connectors import BedrockAgentCoreConnector

if TYPE_CHECKING:
    from mypy_boto3_bedrock_agentcore.type_defs import InvokeAgentRuntimeResponseTypeDef
    from tac.models.session import ConversationSession


class TestBedrockAgentCoreConnector:
    """Test suite for BedrockAgentCoreConnector."""

    def test_initialization(self, mock_tac: MagicMock) -> None:
        """Test connector initialization with invoke function."""
        mock_invoke_fn = MagicMock()

        with patch("tac_aws.connectors.bedrock_agentcore_connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_agentcore_connector.SMSChannel"
        ):
            connector = BedrockAgentCoreConnector(
                tac=mock_tac,
                invoke_fn=mock_invoke_fn,
            )

            # Verify TAC callbacks registered (no conversation_ended callback)
            mock_tac.on_message_ready.assert_called_once()

            # Verify initialization state
            assert connector.tac == mock_tac
            assert connector.invoke_fn == mock_invoke_fn

    def test_initialization_with_channel_configs(self, mock_tac: MagicMock) -> None:
        """Test connector initialization with custom channel configs."""
        mock_invoke_fn = MagicMock()
        sms_config = {"auto_retrieve_memory": True}
        voice_config = {"auto_retrieve_memory": False}

        with patch(
            "tac_aws.connectors.bedrock_agentcore_connector.VoiceChannel"
        ) as MockVoice, patch(
            "tac_aws.connectors.bedrock_agentcore_connector.SMSChannel"
        ) as MockSMS:
            connector = BedrockAgentCoreConnector(
                tac=mock_tac,
                invoke_fn=mock_invoke_fn,
                sms_config=sms_config,
                voice_config=voice_config,
            )

            # Verify channels created with configs
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
        # Mock invoke function
        mock_invoke_fn = MagicMock()
        mock_response: InvokeAgentRuntimeResponseTypeDef = {
            "response": b'{"text": "Test response"}',
            "contentType": "application/json",
            "statusCode": 200,
            "runtimeSessionId": "test_session",
            "mcpSessionId": "",
            "mcpProtocolVersion": "",
            "traceId": "",
            "traceParent": "",
            "traceState": "",
            "baggage": "",
            "ResponseMetadata": {},
        }
        mock_invoke_fn.return_value = mock_response

        with patch("tac_aws.connectors.bedrock_agentcore_connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_agentcore_connector.SMSChannel"
        ), patch("tac_aws.connectors.bedrock_agentcore_connector.MemoryPromptBuilder"):
            connector = BedrockAgentCoreConnector(
                tac=mock_tac,
                invoke_fn=mock_invoke_fn,
            )
            connector.voice.send_response = AsyncMock()

            # Call the handler
            await connector._handle_message(
                user_message="Hello",
                context=mock_conversation_session,
                memory_response=None,
            )

            # Verify invoke function was called with correct parameters
            mock_invoke_fn.assert_called_once_with(
                mock_conversation_session, "Hello", None
            )

            # Verify response was sent to voice channel
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
        mock_response: InvokeAgentRuntimeResponseTypeDef = {
            "response": b'{"text": "Response"}',
            "contentType": "application/json",
            "statusCode": 200,
            "runtimeSessionId": "test_session",
            "mcpSessionId": "",
            "mcpProtocolVersion": "",
            "traceId": "",
            "traceParent": "",
            "traceState": "",
            "baggage": "",
            "ResponseMetadata": {},
        }
        mock_invoke_fn.return_value = mock_response

        with patch("tac_aws.connectors.bedrock_agentcore_connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_agentcore_connector.SMSChannel"
        ), patch(
            "tac_aws.connectors.bedrock_agentcore_connector.MemoryPromptBuilder"
        ) as MockMemoryBuilder:
            MockMemoryBuilder.build = MagicMock(return_value="Memory context")

            connector = BedrockAgentCoreConnector(
                tac=mock_tac,
                invoke_fn=mock_invoke_fn,
            )
            connector.voice.send_response = AsyncMock()

            # Call with memory
            await connector._handle_message(
                user_message="Hello",
                context=mock_conversation_session,
                memory_response=mock_memory_response,
            )

            # Verify memory was built
            MockMemoryBuilder.build.assert_called_once_with(
                mock_memory_response, mock_conversation_session
            )

            # Verify invoke function received memory context
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
        mock_response: InvokeAgentRuntimeResponseTypeDef = {
            "response": b"Voice response",
            "contentType": "text/plain",
            "statusCode": 200,
            "runtimeSessionId": "test_session",
            "mcpSessionId": "",
            "mcpProtocolVersion": "",
            "traceId": "",
            "traceParent": "",
            "traceState": "",
            "baggage": "",
            "ResponseMetadata": {},
        }
        mock_invoke_fn.return_value = mock_response

        with patch("tac_aws.connectors.bedrock_agentcore_connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_agentcore_connector.SMSChannel"
        ), patch("tac_aws.connectors.bedrock_agentcore_connector.MemoryPromptBuilder"):
            connector = BedrockAgentCoreConnector(
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

            # Verify voice channel was used
            connector.voice.send_response.assert_called_once()

            # Verify SMS channel was not used
            connector.sms.send_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_error_handling(
        self,
        mock_tac: MagicMock,
        mock_conversation_session: MagicMock,
    ) -> None:
        """Test error handling during message processing."""
        # Make invoke function raise an error
        mock_invoke_fn = MagicMock(side_effect=Exception("Test error"))

        with patch("tac_aws.connectors.bedrock_agentcore_connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_agentcore_connector.SMSChannel"
        ), patch("tac_aws.connectors.bedrock_agentcore_connector.MemoryPromptBuilder"):
            connector = BedrockAgentCoreConnector(
                tac=mock_tac,
                invoke_fn=mock_invoke_fn,
            )
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

    def test_parse_response_json(self, mock_tac: MagicMock) -> None:
        """Test parsing JSON response."""
        mock_invoke_fn = MagicMock()

        with patch("tac_aws.connectors.bedrock_agentcore_connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_agentcore_connector.SMSChannel"
        ):
            connector = BedrockAgentCoreConnector(
                tac=mock_tac,
                invoke_fn=mock_invoke_fn,
            )

            mock_response: InvokeAgentRuntimeResponseTypeDef = {
                "response": b'{"text": "Hello world"}',
                "contentType": "application/json",
                "statusCode": 200,
                "runtimeSessionId": "test",
                "mcpSessionId": "",
                "mcpProtocolVersion": "",
                "traceId": "",
                "traceParent": "",
                "traceState": "",
                "baggage": "",
                "ResponseMetadata": {},
            }

            result = connector._parse_response(mock_response)
            assert result == "Hello world"

    def test_parse_response_plain_text(self, mock_tac: MagicMock) -> None:
        """Test parsing plain text response."""
        mock_invoke_fn = MagicMock()

        with patch("tac_aws.connectors.bedrock_agentcore_connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_agentcore_connector.SMSChannel"
        ):
            connector = BedrockAgentCoreConnector(
                tac=mock_tac,
                invoke_fn=mock_invoke_fn,
            )

            mock_response: InvokeAgentRuntimeResponseTypeDef = {
                "response": b"Plain text response",
                "contentType": "text/plain",
                "statusCode": 200,
                "runtimeSessionId": "test",
                "mcpSessionId": "",
                "mcpProtocolVersion": "",
                "traceId": "",
                "traceParent": "",
                "traceState": "",
                "baggage": "",
                "ResponseMetadata": {},
            }

            result = connector._parse_response(mock_response)
            assert result == "Plain text response"
