"""Strands SDK connector with channel management."""

from __future__ import annotations

from collections.abc import Callable
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

if TYPE_CHECKING:
    from strands import Agent

logger = get_logger(__name__)


class StrandsConnector:
    """
    Connector for AWS Strands SDK with multi-channel support.

    Combines agent management with channel handling:

    - Creates one Strands agent instance per conversation for proper isolation
    - Manages every channel TAC supports — Voice, SMS, RCS, WhatsApp, and Chat
    - Handles memory injection and message routing

    Args:
        tac: TAC instance for channel integration
        agent_factory: Factory function that creates a new Agent instance.
            Receives ConversationSession context to enable SessionManager usage
            and context-aware agent configuration.
        sms_config: Optional SMS channel configuration (SMSChannelConfig or dict)
        voice_config: Optional Voice channel configuration (VoiceChannelConfig or dict)
        rcs_config: RCS channel configuration. Pass it — `{}` for defaults — to
            enable RCS. Requires `TWILIO_RCS_SENDER_ID`.
        whatsapp_config: WhatsApp channel configuration. Pass it — `{}` for
            defaults — to enable WhatsApp. Requires `TWILIO_WHATSAPP_NUMBER`.
        chat_config: Chat channel configuration. Pass it — `{}` for defaults —
            to enable web chat.

    Attributes:
        channels: The full `ConnectorChannels` set. `channels.messaging` is the
            list to hand a server as `messaging_channels=`.
        voice: VoiceChannel instance for voice conversations
        sms: SMSChannel instance for SMS conversations
        rcs: RCSChannel, or None when `rcs_config` was not given
        whatsapp: WhatsAppChannel, or None when `whatsapp_config` was not given
        chat: ChatChannel, or None when `chat_config` was not given

    Example:
        ```python
        from tac import TAC, TACConfig
        from tac.server import TACFastAPIServer
        from tac.models.session import ConversationSession
        from tac_aws.connectors import StrandsConnector
        from strands import Agent
        from strands.session.file import FileSessionManager

        tac = TAC(config=TACConfig.from_env())

        # Agent factory with context for SessionManager
        def create_agent(context: ConversationSession) -> Agent:
            return Agent(
                model="amazon.nova-pro-v1:0",
                system_prompt="You are helpful.",
                session_manager=FileSessionManager(
                    session_id=context.conversation_id,
                    base_path="./sessions"
                )
            )

        # Create connector with agent factory, plus WhatsApp alongside SMS
        connector = StrandsConnector(
            tac=tac, agent_factory=create_agent, whatsapp_config={}
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
        agent_factory: Callable[[ConversationSession], Agent],
        sms_config: SMSChannelConfig | dict[str, Any] | None = None,
        voice_config: VoiceChannelConfig | dict[str, Any] | None = None,
        rcs_config: RCSChannelConfig | dict[str, Any] | None = None,
        whatsapp_config: WhatsAppChannelConfig | dict[str, Any] | None = None,
        chat_config: ChatChannelConfig | dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize Strands connector with agent factory and channel configs.

        Args:
            tac: TAC instance
            agent_factory: Factory function that creates a new Agent instance.
                Receives ConversationSession context as parameter.
            sms_config: Optional SMS channel configuration
            voice_config: Optional Voice channel configuration
            rcs_config: RCS channel configuration; pass it to enable RCS
            whatsapp_config: WhatsApp channel configuration; pass it to enable WhatsApp
            chat_config: Chat channel configuration; pass it to enable web chat
        """
        self.tac = tac
        self.tac.register_partner_connector(PartnerConnector.AWS_STRANDS, _tac_aws_version)
        self.agent_factory = agent_factory

        # Per-conversation agent management (from adapter)
        self.conversation_agents: dict[str, Agent] = {}

        # Create channels (from handler)
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

        # Track which sessions have been initialized (for memory injection)
        self.initialized_sessions: set[str] = set()

        # Register callbacks with TAC
        self.tac.on_message_ready(self._handle_message)
        self.tac.on_conversation_ended(self._handle_conversation_ended)

        logger.debug("StrandsConnector initialized")

    async def _handle_message(
        self,
        user_message: str,
        context: ConversationSession,
        memory_response: TACMemoryResponse | None,
    ) -> str | None:
        """
        Handler that processes messages through Strands agent and routes responses.

        Manages per-conversation agents, injects memory context, and routes
        responses to appropriate channels.

        Args:
            user_message: The user's message text
            context: Conversation session with metadata
            memory_response: Retrieved memory (if memory_mode="always")
        """
        try:
            conv_id = context.conversation_id

            # Get or create agent for this conversation
            if conv_id not in self.conversation_agents:
                self.conversation_agents[conv_id] = self.agent_factory(context)

            agent = self.conversation_agents[conv_id]

            # For new sessions, inject memory context if available
            if conv_id not in self.initialized_sessions:
                self.initialized_sessions.add(conv_id)

                # Inject memory context if retrieved
                if memory_response:
                    memory_context = MemoryPromptBuilder.build(memory_response, context)
                    if memory_context:
                        # Send memory context to agent first
                        await agent.invoke_async(memory_context)

            # Send user message to agent
            result = await agent.invoke_async(user_message)
            response_text = str(result)

            # Route response to the appropriate channel
            await self.channels.send(context, response_text)

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

    def _handle_conversation_ended(self, context: ConversationSession) -> None:
        """
        Handler called when TAC signals a conversation has ended.

        Automatically cleans up agent resources for the conversation.

        Args:
            context: ConversationSession for the ended conversation
        """
        conversation_id = context.conversation_id

        # Cleanup agent resources
        if conversation_id in self.conversation_agents:
            self.conversation_agents[conversation_id].cleanup()
            del self.conversation_agents[conversation_id]

        # Remove from initialized sessions
        self.initialized_sessions.discard(conversation_id)

        logger.debug(
            "Cleaned up agent resources for ended conversation",
            conversation_id=conversation_id,
        )
