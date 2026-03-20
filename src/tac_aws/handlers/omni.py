"""Channel handlers with conversation management for OmniChannel servers."""

from __future__ import annotations

from typing import Any

from tac.adapters import MemoryPromptBuilder
from tac.channels.sms import SMSChannel
from tac.channels.voice import VoiceChannel
from tac.core.logging import get_logger
from tac.core.tac import TAC
from tac.models.session import ConversationSession
from tac.models.tac import TACMemoryResponse

from tac_aws.adapters.base import BaseAgentAdapter

logger = get_logger(__name__)


class OmniChannelHandlers:
    """
    Multi-channel conversation handler with message processing.

    Manages conversation history, memory injection, agent invocation,
    and response routing across multiple channels (Voice, SMS).

    This class separates conversation management from HTTP routing,
    making it reusable across different server implementations.

    Args:
        tac: TAC instance for channel integration
        adapter: Agent adapter (StrandsAdapter, BedrockAdapter, etc.)
        voice: Optional VoiceChannel handler instance
        sms: Optional SMSChannel handler instance

    Example:
        ```python
        from tac import TAC, TACConfig
        from tac.channels import VoiceChannel, SMSChannel
        from tac_aws.adapters import StrandsAdapter
        from tac_aws.handlers import OmniChannelHandlers
        from strands import Agent

        tac = TAC(config=TACConfig.from_env())
        agent = Agent(model="gpt-4o")
        adapter = StrandsAdapter(agent)

        # Create handlers with conversation management
        handlers = OmniChannelHandlers(
            tac=tac,
            adapter=adapter,
            voice=VoiceChannel(tac=tac, auto_retrieve_memory=True),
            sms=SMSChannel(tac=tac, auto_retrieve_memory=True),
        )

        # Handlers automatically process messages via TAC callbacks
        # Pass to server for HTTP routing
        server = OmniChannelFastAPIServer(handlers=handlers)
        ```
    """

    def __init__(
        self,
        tac: TAC,
        adapter: BaseAgentAdapter,
        voice: VoiceChannel | None = None,
        sms: SMSChannel | None = None,
    ) -> None:
        self.tac = tac
        self.adapter = adapter
        self.voice = voice
        self.sms = sms

        # Track conversation history per conversation ID
        # Format: {'role': 'user'|'assistant', 'content': [{'text': '...'}]}
        self.conversation_history: dict[str, list[dict[str, Any]]] = {}

        # Register message handler with TAC
        self.tac.on_message_ready(self._handle_message_internal)

        logger.info(f"Initialized {self}")

    async def _handle_message_internal(
        self,
        user_message: str,
        context: ConversationSession,
        memory_response: TACMemoryResponse | None,
    ) -> None:
        """Internal handler that processes messages with conversation history and memory.

        This method is called by TAC when a message is ready to be processed.
        It manages conversation history, injects memory context, invokes the agent,
        and routes responses to the appropriate channel.

        Args:
            user_message: The user's message text
            context: Conversation session with metadata
            memory_response: Retrieved memory (if auto_retrieve_memory=True)
        """
        try:
            conv_id = context.conversation_id

            # Initialize conversation history for new conversations
            if conv_id not in self.conversation_history:
                self.conversation_history[conv_id] = []

                # Inject memory as initial context using TAC's MemoryPromptBuilder
                if memory_response:
                    memory_context = MemoryPromptBuilder.build(memory_response, context)
                    if memory_context:
                        # Add memory context as initial user message
                        self.conversation_history[conv_id].append(
                            {"role": "user", "content": [{"text": memory_context}]}
                        )
                        # Add assistant acknowledgment
                        self.conversation_history[conv_id].append(
                            {
                                "role": "assistant",
                                "content": [
                                    {"text": "I understand. I'll use this context to help you."}
                                ],
                            }
                        )

            # Add user message to conversation history
            self.conversation_history[conv_id].append(
                {"role": "user", "content": [{"text": user_message}]}
            )

            # Call agent adapter with conversation history
            # Pass full history to ensure isolation between conversations
            response_text = await self.adapter.run_async(
                message=self.conversation_history[conv_id],  # type: ignore[arg-type]
                session_id=conv_id,
            )

            # Save assistant response to conversation history
            self.conversation_history[conv_id].append(
                {"role": "assistant", "content": [{"text": response_text}]}
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

    def __repr__(self) -> str:
        channels = []
        if self.voice:
            channels.append("voice")
        if self.sms:
            channels.append("sms")
        return f"OmniChannelHandlers({', '.join(channels)})"
