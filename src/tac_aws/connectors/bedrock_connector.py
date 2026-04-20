"""AWS Bedrock Agent connector with channel management."""

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
    from mypy_boto3_bedrock_agent_runtime.client import AgentsforBedrockRuntimeClient
    from mypy_boto3_bedrock_agent_runtime.type_defs import (
        InvokeAgentRequestTypeDef,
        InvokeAgentResponseTypeDef,
    )

logger = get_logger(__name__)


class BedrockConnector:
    """
    Connector for AWS Bedrock Agents with multi-channel support.

    Supports two usage patterns:
    1. Simple config-based (recommended for most users)
    2. Custom invoke function (for advanced use cases needing dynamic behavior)

    Args:
        tac: TAC instance for channel integration
        bedrock_client: AWS Bedrock Agent Runtime client (required if using config)
        config: Static configuration dict for invoke_agent() call (InvokeAgentRequestTypeDef).
            Required fields agentId, agentAliasId will be used. sessionId and inputText
            are auto-injected by connector. (required if using config pattern)
        invoke_fn: Custom function to invoke agent. Receives:
            - context: ConversationSession with conversation_id, channel, etc.
            - user_message: The user's message text
            - memory_context: Optional memory context string (from TAC memory)
            Returns: InvokeAgentResponseTypeDef from client.invoke_agent()
            (required if not using config pattern)
        sms_config: Optional SMS channel configuration (SMSChannelConfig or dict)
        voice_config: Optional Voice channel configuration (VoiceChannelConfig or dict)

    Attributes:
        voice: VoiceChannel instance for voice conversations
        sms: SMSChannel instance for SMS conversations

    Example (Simple - Recommended):
        ```python
        import boto3
        from tac import TAC, TACConfig
        from tac.server import TACFastAPIServer
        from tac_aws.connectors import BedrockConnector

        tac = TAC(config=TACConfig.from_env())
        client = boto3.client("bedrock-agent-runtime", region_name="us-east-1")

        # Simple config-based approach
        connector = BedrockConnector(
            tac=tac,
            bedrock_client=client,
            config={
                "agentId": "AGENT123",
                "agentAliasId": "TSTALIASID",
                "enableTrace": False,  # Optional parameters
            }
        )

        server = TACFastAPIServer(tac=tac, voice_channel=connector.voice, sms_channel=connector.sms)
        server.start()
        ```

    Example (Advanced - Custom Logic):
        ```python
        import boto3
        from tac import TAC, TACConfig
        from tac.models.session import ConversationSession
        from tac.server import TACFastAPIServer
        from tac_aws.connectors import BedrockConnector

        tac = TAC(config=TACConfig.from_env())
        client = boto3.client("bedrock-agent-runtime", region_name="us-east-1")

        # Custom invoke function for dynamic behavior
        def invoke_agent(
            context: ConversationSession,
            user_message: str,
            memory_context: str | None
        ):
            # Dynamic agent selection based on channel
            agent_id = "VOICE_AGENT" if context.channel == "voice" else "SMS_AGENT"

            full_message = user_message
            if memory_context:
                full_message = f"{memory_context}\\n\\nUser: {user_message}"

            return client.invoke_agent(
                agentId=agent_id,
                agentAliasId="TSTALIASID",
                sessionId=context.conversation_id,
                inputText=full_message
            )

        connector = BedrockConnector(tac=tac, invoke_fn=invoke_agent)

        server = TACFastAPIServer(tac=tac, voice_channel=connector.voice, sms_channel=connector.sms)
        server.start()
        ```
    """

    def __init__(
        self,
        tac: TAC,
        bedrock_client: AgentsforBedrockRuntimeClient | None = None,
        config: InvokeAgentRequestTypeDef | dict[str, Any] | None = None,
        invoke_fn: Callable[[ConversationSession, str, str | None], InvokeAgentResponseTypeDef]
        | None = None,
        sms_config: SMSChannelConfig | dict[str, Any] | None = None,
        voice_config: VoiceChannelConfig | dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize Bedrock Agent connector.

        Args:
            tac: TAC instance
            bedrock_client: AWS Bedrock Agent Runtime client (required if using config)
            config: Static invoke_agent config dict (required if using config pattern)
            invoke_fn: Custom invoke function (required if not using config pattern)
            sms_config: Optional SMS channel configuration
            voice_config: Optional Voice channel configuration

        Raises:
            ValueError: If both invoke_fn and config are provided, or neither are provided
        """
        self.tac = tac

        # Validate: Either invoke_fn OR (bedrock_client + config)
        if invoke_fn is not None:
            if bedrock_client is not None or config is not None:
                raise ValueError(
                    "Cannot use both invoke_fn and config-based approach. "
                    "Provide either invoke_fn OR (bedrock_client + config)."
                )
            self.invoke_fn = invoke_fn
            logger.debug("BedrockConnector initialized with custom invoke_fn")
        elif bedrock_client is not None and config is not None:
            # Build invoke function from config
            self.invoke_fn = self._build_invoke_fn_from_config(bedrock_client, config)
            logger.debug("BedrockConnector initialized with config-based approach")
        else:
            raise ValueError(
                "Must provide either invoke_fn OR (bedrock_client + config). "
                "Got neither or incomplete config parameters."
            )

        # Create channels
        self.voice = VoiceChannel(tac=tac, config=voice_config)
        self.sms = SMSChannel(tac=tac, config=sms_config)

        # Register callbacks with TAC
        self.tac.on_message_ready(self._handle_message)

    def _build_invoke_fn_from_config(
        self,
        client: AgentsforBedrockRuntimeClient,
        base_config: InvokeAgentRequestTypeDef | dict[str, Any],
    ) -> Callable[[ConversationSession, str, str | None], InvokeAgentResponseTypeDef]:
        """
        Build an invoke function from static config.

        Args:
            client: Bedrock Agent Runtime client
            base_config: Base configuration for invoke_agent

        Returns:
            Function that invokes agent with merged config
        """

        def invoke_with_config(
            context: ConversationSession,
            user_message: str,
            memory_context: str | None,
        ) -> InvokeAgentResponseTypeDef:
            # Build full message with memory context
            full_message = user_message
            if memory_context:
                full_message = f"{memory_context}\n\nUser: {user_message}"

            # Merge base config with auto-injected values
            merged_config: dict[str, Any] = {
                **base_config,
                "sessionId": context.conversation_id,
                "inputText": full_message,
            }

            return client.invoke_agent(**merged_config)

        return invoke_with_config

    async def _handle_message(
        self,
        user_message: str,
        context: ConversationSession,
        memory_response: TACMemoryResponse | None,
    ) -> str | None:
        """
        Handler that processes messages through user's invoke function and routes responses.

        Builds memory context if available, calls user's invoke function,
        then parses the streaming response.

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

            # Parse streaming response
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
                await self.voice.send_response(context.conversation_id, error_msg, role="assistant")
            elif context.channel == "sms" and self.sms:
                await self.sms.send_response(context.conversation_id, error_msg, role="assistant")

        return None

    def _parse_response(self, response: InvokeAgentResponseTypeDef) -> str:
        """
        Parse streaming response from invoke_agent.

        Args:
            response: InvokeAgentResponseTypeDef from client.invoke_agent()

        Returns:
            Response text string
        """
        # Parse streaming completion
        full_response = ""
        for event in response.get("completion", []):
            if "chunk" in event:
                chunk = event["chunk"]
                if "bytes" in chunk:
                    text = chunk["bytes"].decode("utf-8")
                    full_response += text

        return full_response.strip()
