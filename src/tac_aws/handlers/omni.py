"""Channel handlers with conversation management for OmniChannel servers."""

from __future__ import annotations

from typing import Any

from tac.adapters import MemoryPromptBuilder
from tac.channels.sms import SMSChannel, SMSChannelConfig
from tac.channels.voice import VoiceChannel, VoiceChannelConfig
from tac.core.logging import get_logger
from tac.core.tac import TAC
from tac.models.session import ConversationSession
from tac.models.tac import TACMemoryResponse

from tac_aws.adapters.base import BaseAgentAdapter

logger = get_logger(__name__)


class OmniChannelHandler:
    """
    Multi-channel conversation handler with message processing.

    Creates Voice and SMS channels internally and manages conversation flow
    through the adapter. Provides access to channels for server integration.

    Args:
        tac: TAC instance for channel integration
        adapter: Agent adapter (StrandsAdapter, BedrockAdapter, etc.)
        sms_config: Optional SMS channel configuration (SMSChannelConfig or dict)
        voice_config: Optional Voice channel configuration (VoiceChannelConfig or dict)

    Attributes:
        voice: VoiceChannel instance for voice conversations
        sms: SMSChannel instance for SMS conversations

    Example:
        ```python
        from tac import TAC, TACConfig
        from tac.server import TACFastAPIServer
        from tac.channels.sms import SMSChannelConfig
        from tac.channels.voice import VoiceChannelConfig
        from tac_aws.adapters import StrandsAdapter
        from tac_aws.handlers import OmniChannelHandler
        from strands import Agent

        tac = TAC(config=TACConfig.from_env())
        adapter = StrandsAdapter(agent_factory=lambda: Agent(model="gpt-4o"))

        # Configure channels
        sms_config = SMSChannelConfig(auto_retrieve_memory=True, dedup_capacity=20000)
        voice_config = VoiceChannelConfig(auto_retrieve_memory=True)

        handler = OmniChannelHandler(
            tac=tac,
            adapter=adapter,
            sms_config=sms_config,
            voice_config=voice_config
        )

        # Use handler's channels for server
        server = TACFastAPIServer(tac=tac, voice_channel=handler.voice, sms_channel=handler.sms)
        server.start()
        ```
    """

    def __init__(
        self,
        tac: TAC,
        adapter: BaseAgentAdapter,
        sms_config: SMSChannelConfig | dict[str, Any] | None = None,
        voice_config: VoiceChannelConfig | dict[str, Any] | None = None,
    ) -> None:
        self.tac = tac
        self.adapter = adapter

        # Create channels with configs (use defaults if None)
        self.voice = VoiceChannel(tac=tac, config=voice_config)
        self.sms = SMSChannel(tac=tac, config=sms_config)

        # Track which sessions have been initialized (for memory injection)
        self.initialized_sessions: set[str] = set()

        # Always auto-inject memory context when available
        # Users control memory behavior via auto_retrieve_memory in channels
        self.auto_inject_memory = True

        # Register message handler with TAC
        self.tac.on_message_ready(self._handle_message)

        logger.info("OmniChannelHandler initialized")

    async def _handle_message(
        self,
        user_message: str,
        context: ConversationSession,
        memory_response: TACMemoryResponse | None,
    ) -> None:
        """Handler that processes messages and routes them through the adapter.

        The adapter is responsible for managing conversation history in an SDK-specific way.
        This handler focuses on memory injection and channel routing.

        Args:
            user_message: The user's message text
            context: Conversation session with metadata
            memory_response: Retrieved memory (if auto_retrieve_memory=True)
        """
        try:
            conv_id = context.conversation_id

            # For new sessions, inject memory context if configured
            if conv_id not in self.initialized_sessions:
                self.initialized_sessions.add(conv_id)

                # Auto-inject memory if configured
                if self.auto_inject_memory and memory_response:
                    memory_context = MemoryPromptBuilder.build(memory_response, context)
                    if memory_context:
                        # Send memory context to adapter first
                        await self.adapter.run_async(
                            message=memory_context, conversation_id=conv_id
                        )

            # Send user message to adapter
            # Adapter manages conversation history in SDK-specific way
            response_text = await self.adapter.run_async(
                message=user_message, conversation_id=conv_id
            )

            # Automatically route response to the appropriate channel
            if context.channel == "voice" and self.voice:
                await self.voice.send_response(
                    context.conversation_id, response_text, role="assistant"
                )
            elif context.channel == "sms" and self.sms:
                await self.sms.send_response(
                    context.conversation_id, response_text, role="assistant"
                )
            else:
                logger.error(
                    f"No channel handler for {context.channel}",
                    conversation_id=context.conversation_id,
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
                await self.voice.send_response(
                    context.conversation_id, error_msg, role="assistant"
                )
            elif context.channel == "sms" and self.sms:
                await self.sms.send_response(
                    context.conversation_id, error_msg, role="assistant"
                )
