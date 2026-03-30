"""Bedrock Agent Core connector with channel management."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from tac.adapters import MemoryPromptBuilder
from tac.channels.sms import SMSChannel, SMSChannelConfig
from tac.channels.voice import VoiceChannel, VoiceChannelConfig
from tac.core.logging import get_logger
from tac.core.tac import TAC
from tac.models.session import ConversationSession
from tac.models.tac import TACMemoryResponse

if TYPE_CHECKING:
    from mypy_boto3_bedrock_agentcore.type_defs import InvokeAgentRuntimeResponseTypeDef

logger = get_logger(__name__)


class BedrockAgentCoreConnector:
    """
    Connector for AWS Bedrock Agent Core with multi-channel support.

    Invokes agents via user-provided function that receives conversation context.
    Users create the bedrock-agentcore client and define invoke logic.

    Args:
        tac: TAC instance for channel integration
        invoke_fn: Function to invoke agent. Receives:
            - context: ConversationSession with conversation_id, channel, etc.
            - user_message: The user's message text
            - memory_context: Optional memory context string (from TAC memory)
            Returns: InvokeAgentRuntimeResponseTypeDef from agentcore_client.invoke_agent_runtime()
        sms_config: Optional SMS channel configuration (SMSChannelConfig or dict)
        voice_config: Optional Voice channel configuration (VoiceChannelConfig or dict)

    Attributes:
        voice: VoiceChannel instance for voice conversations
        sms: SMSChannel instance for SMS conversations

    Example:
        ```python
        import boto3
        import json
        from tac import TAC, TACConfig
        from tac.models.session import ConversationSession
        from tac.server import TACFastAPIServer
        from tac_aws.connectors import BedrockAgentCoreConnector

        tac = TAC(config=TACConfig.from_env())

        # Create client with your config
        agentcore_client = boto3.client("bedrock-agentcore", region_name="us-east-1")

        # Define invoke function - just call and return response
        def invoke_agent(
            context: ConversationSession,
            user_message: str,
            memory_context: str | None
        ) -> dict:
            # Build payload with context-aware logic
            payload_data = {
                "prompt": user_message,
                "channel": context.channel,
            }
            if memory_context:
                payload_data["memory_context"] = memory_context

            payload = json.dumps(payload_data).encode("utf-8")

            # Invoke with your ARN and return response object
            return agentcore_client.invoke_agent_runtime(
                agentRuntimeArn="arn:aws:bedrock-agentcore:us-east-1:123456789:agent-runtime/...",
                runtimeSessionId=context.conversation_id,
                payload=payload,
            )

        # Create connector with your invoke function
        connector = BedrockAgentCoreConnector(tac=tac, invoke_fn=invoke_agent)

        # Use connector's channels for server
        server = TACFastAPIServer(tac=tac, voice_channel=connector.voice, sms_channel=connector.sms)
        server.start()
        ```
    """

    def __init__(
        self,
        tac: TAC,
        invoke_fn: Callable[
            [ConversationSession, str, str | None], InvokeAgentRuntimeResponseTypeDef
        ],
        sms_config: SMSChannelConfig | dict[str, Any] | None = None,
        voice_config: VoiceChannelConfig | dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize Bedrock Agent Core connector.

        Args:
            tac: TAC instance
            invoke_fn: Function to invoke agent that returns response object
            sms_config: Optional SMS channel configuration
            voice_config: Optional Voice channel configuration
        """
        self.tac = tac
        self.invoke_fn = invoke_fn

        # Create channels
        self.voice = VoiceChannel(tac=tac, config=voice_config)
        self.sms = SMSChannel(tac=tac, config=sms_config)

        # Register callbacks with TAC
        self.tac.on_message_ready(self._handle_message)

        logger.debug("BedrockAgentCoreConnector initialized")

    async def _handle_message(
        self,
        user_message: str,
        context: ConversationSession,
        memory_response: TACMemoryResponse | None,
    ) -> None:
        """
        Handler that processes messages through user's invoke function and routes responses.

        Builds memory context if available, calls user's invoke function,
        then parses the response.

        Args:
            user_message: The user's message text
            context: Conversation session with metadata
            memory_response: Retrieved memory (if auto_retrieve_memory=True)
        """
        try:
            # Build memory context if available
            memory_context: str | None = None
            if memory_response:
                memory_context = MemoryPromptBuilder.build(memory_response, context)

            # Call user's invoke function to get response object
            response = self.invoke_fn(context, user_message, memory_context)

            # Parse response (sync way)
            response_text = self._parse_response(response)

            # Route response to the appropriate channel
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


    def _parse_response(self, response: InvokeAgentRuntimeResponseTypeDef) -> str:
        """
        Parse response from invoke_agent_runtime (sync way).

        Args:
            response: InvokeAgentRuntimeResponseTypeDef from agentcore_client.invoke_agent_runtime()

        Returns:
            Response text string
        """
        import json

        # Get StreamingBody from response
        streaming_body = response.get("response")

        # Read all bytes from StreamingBody
        if streaming_body and hasattr(streaming_body, "read"):
            response_bytes = streaming_body.read()
        elif isinstance(streaming_body, bytes):
            response_bytes = streaming_body
        else:
            response_bytes = b""

        # Convert to string
        response_body = response_bytes.decode("utf-8") if response_bytes else ""

        # Try to parse as JSON
        try:
            data = json.loads(response_body)
            # Extract text field or convert to string
            if isinstance(data, dict):
                text = data.get("text") or data.get("response") or str(data)
                return str(text)
            return str(data)
        except (json.JSONDecodeError, ValueError):
            # If not JSON, return as plain text
            return response_body
