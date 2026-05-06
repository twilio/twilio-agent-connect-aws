"""Tests for BedrockAgentCoreConnector."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tac_aws.connectors import BedrockAgentCoreConnector

if TYPE_CHECKING:
    from mypy_boto3_bedrock_agentcore.type_defs import InvokeAgentRuntimeResponseTypeDef


class TestBedrockAgentCoreConnector:
    """Test suite for BedrockAgentCoreConnector."""

    def test_initialization(self, mock_tac: MagicMock) -> None:
        """Test connector initialization with HTTP runtime."""
        mock_invoke_fn = MagicMock()

        with patch("tac_aws.connectors.bedrock_agentcore.connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_agentcore.connector.SMSChannel"
        ):
            connector = BedrockAgentCoreConnector(
                tac=mock_tac,
                runtime={"http": mock_invoke_fn},
            )

            # Verify TAC callbacks registered (no conversation_ended callback)
            mock_tac.on_message_ready.assert_called_once()

            # Verify initialization state
            assert connector.tac == mock_tac
            assert connector.invoke_fn == mock_invoke_fn

    def test_initialization_with_channel_configs(self, mock_tac: MagicMock) -> None:
        """Test connector initialization with custom channel configs."""
        mock_invoke_fn = MagicMock()
        sms_config = {"memory_mode": "always"}
        voice_config = {"memory_mode": "never"}

        with patch(
            "tac_aws.connectors.bedrock_agentcore.connector.VoiceChannel"
        ) as mock_voice, patch(
            "tac_aws.connectors.bedrock_agentcore.connector.SMSChannel"
        ) as mock_sms:
            connector = BedrockAgentCoreConnector(
                tac=mock_tac,
                runtime={"http": mock_invoke_fn},
                sms_config=sms_config,
                voice_config=voice_config,
            )

            # Verify channels created with configs
            mock_voice.assert_called_once_with(tac=mock_tac, config=voice_config)
            mock_sms.assert_called_once_with(tac=mock_tac, config=sms_config)
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

        with patch("tac_aws.connectors.bedrock_agentcore.connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_agentcore.connector.SMSChannel"
        ), patch("tac_aws.connectors.bedrock_agentcore.connector.MemoryPromptBuilder"):
            connector = BedrockAgentCoreConnector(
                tac=mock_tac,
                runtime={"http": mock_invoke_fn},
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

            # Verify response was sent to voice channel (streaming with AsyncGenerator)
            from collections.abc import AsyncGenerator

            assert connector.voice.send_response.call_count == 1
            call_args = connector.voice.send_response.call_args
            assert call_args[0][0] == "test_conv_123"  # conversation_id
            assert isinstance(call_args[0][1], AsyncGenerator)  # response is async generator
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

        with patch("tac_aws.connectors.bedrock_agentcore.connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_agentcore.connector.SMSChannel"
        ), patch(
            "tac_aws.connectors.bedrock_agentcore.connector.MemoryPromptBuilder"
        ) as mock_memory_builder:
            mock_memory_builder.build = MagicMock(return_value="Memory context")

            connector = BedrockAgentCoreConnector(
                tac=mock_tac,
                runtime={"http": mock_invoke_fn},
            )
            connector.voice.send_response = AsyncMock()

            # Call with memory
            await connector._handle_message(
                user_message="Hello",
                context=mock_conversation_session,
                memory_response=mock_memory_response,
            )

            # Verify memory was built
            mock_memory_builder.build.assert_called_once_with(
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

        with patch("tac_aws.connectors.bedrock_agentcore.connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_agentcore.connector.SMSChannel"
        ), patch("tac_aws.connectors.bedrock_agentcore.connector.MemoryPromptBuilder"):
            connector = BedrockAgentCoreConnector(
                tac=mock_tac,
                runtime={"http": mock_invoke_fn},
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

        with patch("tac_aws.connectors.bedrock_agentcore.connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_agentcore.connector.SMSChannel"
        ), patch("tac_aws.connectors.bedrock_agentcore.connector.MemoryPromptBuilder"):
            connector = BedrockAgentCoreConnector(
                tac=mock_tac,
                runtime={"http": mock_invoke_fn},
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

    def test_initialization_with_websocket(self, mock_tac: MagicMock) -> None:
        """Test connector initialization with WebSocket config."""
        mock_invoke_fn = MagicMock()
        mock_ws_factory = AsyncMock()
        mock_payload_fn = MagicMock()

        with patch("tac_aws.connectors.bedrock_agentcore.connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_agentcore.connector.SMSChannel"
        ):
            from tac_aws.connectors.bedrock_agentcore.config import RuntimeConfig, WebSocketConfig

            connector = BedrockAgentCoreConnector(
                tac=mock_tac,
                runtime=RuntimeConfig(
                    http=mock_invoke_fn,
                    websocket=WebSocketConfig(
                        factory=mock_ws_factory,
                        payload_fn=mock_payload_fn,
                    ),
                ),
            )

            # Verify TAC callbacks registered (including conversation_ended and interrupt)
            assert mock_tac.on_message_ready.call_count == 1
            assert mock_tac.on_conversation_ended.call_count == 1
            assert mock_tac.on_interrupt.call_count == 1

            # Verify WebSocket config stored
            assert connector.websocket_config is not None
            assert connector.websocket_config.factory == mock_ws_factory
            assert connector.websocket_config.payload_fn == mock_payload_fn

    @pytest.mark.asyncio
    async def test_handle_message_with_websocket(
        self,
        mock_tac: MagicMock,
        mock_conversation_session: MagicMock,
    ) -> None:
        """Test that voice messages use WebSocket when configured."""
        mock_conversation_session.channel = "voice"
        mock_invoke_fn = MagicMock()
        mock_ws_factory = AsyncMock()
        mock_payload_fn = MagicMock(return_value={"type": "prompt", "voicePrompt": "Hello"})

        # Mock WebSocket
        mock_ws = MagicMock()
        mock_ws.send = AsyncMock()
        mock_ws.__aiter__ = MagicMock(return_value=iter([]))
        mock_ws_factory.return_value = mock_ws

        with patch("tac_aws.connectors.bedrock_agentcore.connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_agentcore.connector.SMSChannel"
        ), patch("tac_aws.connectors.bedrock_agentcore.connector.MemoryPromptBuilder"):
            from tac_aws.connectors.bedrock_agentcore.config import RuntimeConfig, WebSocketConfig

            connector = BedrockAgentCoreConnector(
                tac=mock_tac,
                runtime=RuntimeConfig(
                    http=mock_invoke_fn,
                    websocket=WebSocketConfig(
                        factory=mock_ws_factory,
                        payload_fn=mock_payload_fn,
                    ),
                ),
            )
            connector.voice.send_response = AsyncMock()

            # Call the handler
            await connector._handle_message(
                user_message="Hello",
                context=mock_conversation_session,
                memory_response=None,
            )

            # Verify WebSocket was used (not HTTP)
            mock_ws_factory.assert_called_once_with(mock_conversation_session)
            mock_payload_fn.assert_called_once_with(mock_conversation_session, "Hello", None)
            mock_ws.send.assert_called_once()

            # Verify HTTP was NOT used
            mock_invoke_fn.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_websocket_connection_pooling(
        self,
        mock_tac: MagicMock,
        mock_conversation_session: MagicMock,
    ) -> None:
        """Test that WebSocket connections are pooled per session."""
        mock_conversation_session.channel = "voice"
        mock_invoke_fn = MagicMock()
        mock_ws_factory = AsyncMock()
        mock_payload_fn = MagicMock(return_value={"type": "prompt"})

        # Mock WebSocket with state
        mock_ws = MagicMock()
        mock_ws.send = AsyncMock()
        mock_ws.__aiter__ = MagicMock(return_value=iter([]))
        mock_ws.state = MagicMock()
        mock_ws.state.name = "OPEN"
        mock_ws_factory.return_value = mock_ws

        with patch("tac_aws.connectors.bedrock_agentcore.connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_agentcore.connector.SMSChannel"
        ), patch("tac_aws.connectors.bedrock_agentcore.connector.MemoryPromptBuilder"):
            from tac_aws.connectors.bedrock_agentcore.config import RuntimeConfig, WebSocketConfig

            connector = BedrockAgentCoreConnector(
                tac=mock_tac,
                runtime=RuntimeConfig(
                    http=mock_invoke_fn,
                    websocket=WebSocketConfig(
                        factory=mock_ws_factory,
                        payload_fn=mock_payload_fn,
                    ),
                ),
            )
            connector.voice.send_response = AsyncMock()

            # Send two messages
            await connector._handle_message("Hello", mock_conversation_session, None)
            await connector._handle_message("Hi again", mock_conversation_session, None)

            # Verify factory was called only once (connection reused)
            assert mock_ws_factory.call_count == 1

            # Verify messages were sent through same connection
            assert mock_ws.send.call_count == 2

    @pytest.mark.asyncio
    async def test_handle_conversation_ended_closes_websocket(
        self,
        mock_tac: MagicMock,
        mock_conversation_session: MagicMock,
    ) -> None:
        """Test that WebSocket connection is closed when conversation ends."""
        mock_invoke_fn = MagicMock()
        mock_ws_factory = AsyncMock()
        mock_payload_fn = MagicMock()

        # Mock WebSocket
        mock_ws = MagicMock()
        mock_ws.close = AsyncMock()
        mock_ws.state = MagicMock()
        mock_ws.state.name = "OPEN"

        with patch("tac_aws.connectors.bedrock_agentcore.connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_agentcore.connector.SMSChannel"
        ):
            from tac_aws.connectors.bedrock_agentcore.config import RuntimeConfig, WebSocketConfig

            connector = BedrockAgentCoreConnector(
                tac=mock_tac,
                runtime=RuntimeConfig(
                    http=mock_invoke_fn,
                    websocket=WebSocketConfig(
                        factory=mock_ws_factory,
                        payload_fn=mock_payload_fn,
                    ),
                ),
            )

            # Manually add connection to pool
            connector.agent_connections["test_conv_123"] = mock_ws

            # Call conversation ended
            await connector._handle_conversation_ended(mock_conversation_session)

            # Verify WebSocket was closed
            mock_ws.close.assert_called_once()

            # Verify connection removed from pool
            assert "test_conv_123" not in connector.agent_connections

    @pytest.mark.asyncio
    async def test_handle_interrupt_sends_interrupt_message(
        self,
        mock_tac: MagicMock,
        mock_conversation_session: MagicMock,
    ) -> None:
        """Test that interrupt data is forwarded to agent via WebSocket."""
        mock_invoke_fn = MagicMock()
        mock_ws_factory = AsyncMock()
        mock_payload_fn = MagicMock()

        # Mock WebSocket
        mock_ws = MagicMock()
        mock_ws.send = AsyncMock()

        with patch("tac_aws.connectors.bedrock_agentcore.connector.VoiceChannel"), patch(
            "tac_aws.connectors.bedrock_agentcore.connector.SMSChannel"
        ):
            from tac_aws.connectors.bedrock_agentcore.config import RuntimeConfig, WebSocketConfig

            connector = BedrockAgentCoreConnector(
                tac=mock_tac,
                runtime=RuntimeConfig(
                    http=mock_invoke_fn,
                    websocket=WebSocketConfig(
                        factory=mock_ws_factory,
                        payload_fn=mock_payload_fn,
                    ),
                ),
            )

            # Manually add connection to pool
            connector.agent_connections["test_conv_123"] = mock_ws

            # Call interrupt handler
            interrupt_data = {"utterance_until_interrupt": "Hello wor"}
            await connector._handle_interrupt(mock_conversation_session, interrupt_data)

            # Verify interrupt message was sent
            mock_ws.send.assert_called_once()
            sent_data = mock_ws.send.call_args[0][0]
            import json

            payload = json.loads(sent_data)
            assert payload["type"] == "interrupt"
            assert payload["utterance_until_interrupt"] == "Hello wor"
