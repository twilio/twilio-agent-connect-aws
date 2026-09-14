"""Main BedrockAgentCoreConnector class."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tac import PartnerConnector
from tac.adapters import MemoryPromptBuilder
from tac.channels.chat import ChatChannelConfig
from tac.channels.rcs import RCSChannelConfig
from tac.channels.sms import SMSChannelConfig
from tac.channels.voice import VoiceChannelConfig
from tac.channels.whatsapp import WhatsAppChannelConfig
from tac.core.logging import get_logger
from tac.core.tac import TAC
from tac.models.session import ConversationSession
from tac.models.tac import TACMemoryResponse

from tac_aws._version import __version__ as _tac_aws_version
from tac_aws.connectors.channels import ConnectorChannels

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
        rcs_config: Optional RCS channel tuning (RCSChannelConfig or dict). RCS
            itself is enabled by setting `TWILIO_RCS_SENDER_ID`.
        whatsapp_config: Optional WhatsApp channel tuning (WhatsAppChannelConfig
            or dict). WhatsApp itself is enabled by setting `TWILIO_WHATSAPP_NUMBER`.
        chat_config: Optional Chat channel configuration (ChatChannelConfig or dict)

    Attributes:
        channels: The full `ConnectorChannels` set. `channels.messaging` is the
            list to hand a server as `messaging_channels=`.
        voice: VoiceChannel instance for voice conversations
        sms: SMSChannel instance for SMS conversations
        chat: ChatChannel instance for web chat conversations
        rcs: RCSChannel, or None when no RCS sender ID is configured
        whatsapp: WhatsAppChannel, or None when no WhatsApp number is configured

    Example:
        ```python
        import boto3
        import json
        import websockets
        from bedrock_agentcore.runtime import AgentCoreRuntimeClient
        from tac import TAC, TACConfig
        from tac.models.session import ConversationSession
        from tac.channels.sms import SMSChannelConfig
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
                memory_mode="once",
            ),
            sms_config=SMSChannelConfig(memory_mode="always"),
        )

        # Use connector's channels for server
        server = TACFastAPIServer(
            tac=tac,
            voice_channel=connector.voice,
            messaging_channels=connector.channels.messaging,
        )
        server.start()
        ```
    """

    def __init__(
        self,
        tac: TAC,
        runtime: RuntimeConfig | dict[str, Any],
        sms_config: SMSChannelConfig | dict[str, Any] | None = None,
        voice_config: VoiceChannelConfig | dict[str, Any] | None = None,
        rcs_config: RCSChannelConfig | dict[str, Any] | None = None,
        whatsapp_config: WhatsAppChannelConfig | dict[str, Any] | None = None,
        chat_config: ChatChannelConfig | dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize Bedrock Agent Core connector.

        Args:
            tac: TAC instance
            runtime: Agent runtime configuration (RuntimeConfig or dict)
            sms_config: Optional SMS channel configuration
            voice_config: Optional Voice channel configuration
            rcs_config: Optional RCS channel tuning; TWILIO_RCS_SENDER_ID enables RCS
            whatsapp_config: Optional WhatsApp channel tuning;
                TWILIO_WHATSAPP_NUMBER enables WhatsApp
            chat_config: Optional Chat channel configuration
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
        self.channels = ConnectorChannels(
            tac,
            voice_config=voice_config,
            sms_config=sms_config,
            rcs_config=rcs_config,
            whatsapp_config=whatsapp_config,
            chat_config=chat_config,
        )
        self.voice = self.channels.voice
        self.sms = self.channels.sms
        self.rcs = self.channels.rcs
        self.whatsapp = self.channels.whatsapp
        self.chat = self.channels.chat

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
        - Messaging channels (SMS, RCS, WhatsApp, Chat): Always use HTTP invocation

        Args:
            user_message: The user's message text
            context: Conversation session with metadata
            memory_response: Retrieved memory context (if memory_mode="always")
        """
        try:
            # Build memory context if available
            memory_context: str | None = None
            if memory_response:
                memory_context = MemoryPromptBuilder.build(memory_response, context)

            # Route: prefer WebSocket for voice, otherwise use HTTP
            if context.channel == "VOICE" and self.websocket_config:
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
                # Voice (HTTP fallback) or a messaging channel: Use HTTP streaming
                await http.handle_http_message(
                    self.invoke_fn,
                    user_message,
                    context,
                    memory_context,
                    self.channels,
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
            await self.channels.send(context, error_msg)

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
