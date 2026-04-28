"""Main BedrockAgentCoreConnector class."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tac import PartnerConnector
from tac.adapters import MemoryPromptBuilder
from tac.channels.sms import SMSChannel, SMSChannelConfig
from tac.channels.voice import VoiceChannel, VoiceChannelConfig
from tac.core.logging import get_logger
from tac.core.tac import TAC
from tac.models.session import ConversationSession
from tac.models.tac import TACMemoryResponse

from tac_aws._version import __version__ as _tac_aws_version

from . import http, websocket
from .config import RuntimeConfig

if TYPE_CHECKING:
    from websockets.client import WebSocketClientProtocol

logger = get_logger(__name__)


class BedrockAgentCoreConnector:
    """
    Connector for AWS Bedrock Agent Core with dual-runtime pattern.

    Provides two runtime modes:
    - HTTP invocation (required): For both voice and SMS channels
    - WebSocket streaming (optional): For voice channel low-latency optimization (~50ms vs ~200ms)

    Args:
        tac: TAC instance for channel integration
        runtime: Agent runtime configuration (RuntimeConfig or dict):
            - http: Function to invoke agent via HTTP (required)
                Signature: (context, user_message, memory_context) -> InvokeAgentRuntimeResponseTypeDef
                Users control all invoke_agent_runtime() parameters
            - websocket: Optional WebSocketConfig for voice optimization:
                - factory: Async function to create WebSocket connection
                    Signature: (context) -> WebSocketClientProtocol
                    Called once per session for connection pooling
                - payload_fn: Function to build WebSocket message payload
                    Signature: (context, user_message, memory_context) -> dict[str, Any]
                    Called every message - users control payload format
        sms_config: Optional SMS channel configuration (SMSChannelConfig or dict)
        voice_config: Optional Voice channel configuration (VoiceChannelConfig or dict)

    Attributes:
        voice: VoiceChannel instance for voice conversations
        sms: SMSChannel instance for SMS conversations

    Example:
        ```python
        import boto3
        import json
        import websockets
        from bedrock_agentcore.runtime import AgentCoreRuntimeClient
        from tac import TAC, TACConfig
        from tac.models.session import ConversationSession
        from tac.channels.voice import VoiceChannelConfig
        from tac.server import TACFastAPIServer
        from tac.session import ThreadSafeSessionManager
        from tac_aws.connectors import BedrockAgentCoreConnector
        from tac_aws.connectors.bedrock_agentcore.config import RuntimeConfig, WebSocketConfig
        from websockets.client import WebSocketClientProtocol

        tac = TAC(config=TACConfig.from_env())
        AGENT_ARN = "arn:aws:bedrock-agentcore:us-east-1:123456789:agent-runtime/..."

        # HTTP: boto3 client provides invoke_agent_runtime()
        agentcore_http_client = boto3.client("bedrock-agentcore", region_name="us-east-1")

        def invoke_agent_http(
            context: ConversationSession,
            user_message: str,
            memory_context: str | None
        ) -> dict:
            payload_data = {"prompt": user_message}
            if memory_context:
                payload_data["memory_context"] = memory_context

            payload = json.dumps(payload_data).encode("utf-8")

            return agentcore_http_client.invoke_agent_runtime(
                agentRuntimeArn=AGENT_ARN,
                runtimeSessionId=context.conversation_id,
                payload=payload,
            )

        # WebSocket: AgentCoreRuntimeClient provides generate_ws_connection()
        agentcore_client = AgentCoreRuntimeClient(region="us-east-1")

        async def create_websocket(context: ConversationSession) -> WebSocketClientProtocol:
            ws_url, headers = agentcore_client.generate_ws_connection(
                runtime_arn=AGENT_ARN,
                session_id=context.conversation_id,
            )
            return await websockets.connect(ws_url, additional_headers=headers)

        def build_websocket_payload(
            context: ConversationSession, user_message: str, memory_context: str | None
        ) -> dict[str, Any]:
            payload: dict[str, Any] = {"type": "prompt", "voicePrompt": user_message}
            if memory_context:
                payload["memoryContext"] = memory_context
            return payload

        # Create connector
        connector = BedrockAgentCoreConnector(
            tac=tac,
            runtime=RuntimeConfig(
                http=invoke_agent_http,  # Required: HTTP streaming for both channels
                websocket=WebSocketConfig(  # Optional: WebSocket optimization for voice
                    factory=create_websocket,
                    payload_fn=build_websocket_payload,
                ),
            ),
            voice_config=VoiceChannelConfig(
                session_manager=ThreadSafeSessionManager(),
                auto_retrieve_memory=True,
            ),
        )

        # Use connector's channels for server
        server = TACFastAPIServer(tac=tac, voice_channel=connector.voice, messaging_channels=[connector.sms])
        server.start()
        ```
    """

    def __init__(
        self,
        tac: TAC,
        runtime: RuntimeConfig | dict[str, Any],
        sms_config: SMSChannelConfig | dict[str, Any] | None = None,
        voice_config: VoiceChannelConfig | dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize Bedrock Agent Core connector.

        Args:
            tac: TAC instance
            runtime: Agent runtime configuration (RuntimeConfig or dict)
            sms_config: Optional SMS channel configuration
            voice_config: Optional Voice channel configuration
        """
        self.tac = tac
        self.tac.register_partner_connector(PartnerConnector.AWS_AGENTCORE, _tac_aws_version)

        # Convert dict to RuntimeConfig if needed
        if isinstance(runtime, dict):
            runtime_config = RuntimeConfig(**runtime)
        else:
            runtime_config = runtime

        # Store runtime config
        self.invoke_fn = runtime_config.http
        self.websocket_config = runtime_config.websocket
        self.agent_connections: dict[
            str, WebSocketClientProtocol
        ] = {}  # WebSocket pool: session_id -> connection

        if self.websocket_config:
            logger.info("BedrockAgentCoreConnector: WebSocket enabled for voice channel")

        logger.info("BedrockAgentCoreConnector: initialized with HTTP invocation")

        # Create channels
        self.voice = VoiceChannel(tac=tac, config=voice_config)
        self.sms = SMSChannel(tac=tac, config=sms_config)

        # Register callbacks with TAC
        self.tac.on_message_ready(self._handle_message)
        if self.websocket_config:
            self.tac.on_conversation_ended(self._handle_conversation_ended)
            self.tac.on_interrupt(self._handle_interrupt)

    async def _handle_message(
        self,
        user_message: str,
        context: ConversationSession,
        memory_response: TACMemoryResponse | None,
    ) -> str | None:
        """
        Process incoming message and route response to appropriate channel.

        Routing logic:
        - Voice + WebSocket configured: Use WebSocket streaming (low latency)
        - Voice + WebSocket not configured: Use HTTP streaming (fallback)
        - SMS: Always use HTTP invocation

        Args:
            user_message: The user's message text
            context: Conversation session with metadata
            memory_response: Retrieved memory context (if auto_retrieve_memory=True)
        """
        try:
            # Build memory context if available
            memory_context: str | None = None
            if memory_response:
                memory_context = MemoryPromptBuilder.build(memory_response, context)

            # Route: prefer WebSocket for voice, otherwise use HTTP
            if context.channel == "voice" and self.websocket_config:
                # Voice with WebSocket optimization
                await websocket.handle_websocket_message(
                    self.websocket_config.factory,
                    self.websocket_config.payload_fn,
                    self.agent_connections,
                    context,
                    user_message,
                    memory_context,
                    self.voice,
                )
            else:
                # Voice (HTTP fallback) or SMS: Use HTTP streaming
                await http.handle_http_message(
                    self.invoke_fn,
                    user_message,
                    context,
                    memory_context,
                    self.voice,
                    self.sms,
                )

        except Exception as e:
            logger.error(
                "Error processing message",
                conversation_id=context.conversation_id,
                error=str(e),
                exc_info=True,
            )
            # Send error response
            error_msg = "I encountered an error processing your message. Please try again."
            if context.channel == "voice" and self.voice:
                await self.voice.send_response(context.conversation_id, error_msg, role="assistant")
            elif context.channel == "sms" and self.sms:
                await self.sms.send_response(context.conversation_id, error_msg, role="assistant")

        return None

    async def _handle_conversation_ended(self, context: ConversationSession) -> None:
        """
        Clean up WebSocket connection when conversation ends.

        Args:
            context: Conversation session with metadata
        """
        await websocket.handle_conversation_ended(self.agent_connections, context)

    async def _handle_interrupt(
        self, context: ConversationSession, interrupt_data: dict[str, Any]
    ) -> None:
        """
        Forward interrupt to agent via WebSocket.

        Args:
            context: Conversation session with metadata
            interrupt_data: Interrupt data from TAC (includes utterance_until_interrupt)
        """
        await websocket.handle_interrupt(self.agent_connections, context, interrupt_data)
