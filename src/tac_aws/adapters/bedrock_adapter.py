"""AWS Bedrock Agent Runtime adapter."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, Dict, Optional

from tac_aws.adapters.base import BaseAgentAdapter

if TYPE_CHECKING:
    from mypy_boto3_bedrock_agent_runtime.client import AgentsforBedrockRuntimeClient

logger = logging.getLogger(__name__)


class BedrockAdapter(BaseAgentAdapter):
    """Adapter for AWS Bedrock Agent Runtime."""

    def __init__(
        self,
        client: AgentsforBedrockRuntimeClient,
        agent_id: str,
        agent_alias_id: str = "TSTALIASID",
        enable_trace: bool = False,
        streaming_configurations: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize Bedrock adapter.

        Args:
            client: boto3 bedrock-agent-runtime client
            agent_id: Bedrock agent ID
            agent_alias_id: Bedrock agent alias ID (default: TSTALIASID)
            enable_trace: Enable trace logging (default: False)
            streaming_configurations: Streaming config dict (default: None)
        """
        self.client: AgentsforBedrockRuntimeClient = client
        self.agent_id = agent_id
        self.agent_alias_id = agent_alias_id
        self.enable_trace = enable_trace
        self.streaming_configurations = streaming_configurations

    async def run_async(self, message: str, session_id: str, **kwargs: Any) -> str:
        """
        Run Bedrock agent asynchronously.

        Args:
            message: Input text
            session_id: Session ID for conversation state
            **kwargs: Additional parameters for invoke_agent()

        Returns:
            Complete response text from agent
        """
        invoke_params: Dict[str, Any] = {
            "agentId": self.agent_id,
            "agentAliasId": self.agent_alias_id,
            "sessionId": session_id,
            "inputText": message,
        }

        # Add optional parameters
        if self.enable_trace:
            invoke_params["enableTrace"] = True
        if self.streaming_configurations:
            invoke_params["streamingConfigurations"] = self.streaming_configurations

        # Override with any kwargs
        invoke_params.update(kwargs)

        response = self.client.invoke_agent(**invoke_params)

        # Extract completion from streaming response
        completion = ""
        for event in response.get("completion", []):
            # Collect agent output
            if "chunk" in event:
                chunk_data = event["chunk"]
                if "bytes" in chunk_data:
                    completion += chunk_data["bytes"].decode("utf-8")

            # Log trace output if enabled
            if "trace" in event and self.enable_trace:
                trace_event = event.get("trace")
                if trace_event:
                    trace = trace_event.get("trace", {})
                    for key, value in trace.items():
                        logger.info("%s: %s", key, value)

        return completion if completion else ""

    async def stream_async(
        self, message: str, session_id: str, **kwargs: Any
    ) -> AsyncIterator[str]:
        """
        Run Bedrock agent with streaming.

        Args:
            message: Input text
            session_id: Session ID for conversation state
            **kwargs: Additional parameters for invoke_agent()

        Yields:
            Response text chunks
        """
        invoke_params: Dict[str, Any] = {
            "agentId": self.agent_id,
            "agentAliasId": self.agent_alias_id,
            "sessionId": session_id,
            "inputText": message,
        }

        # Add optional parameters
        if self.enable_trace:
            invoke_params["enableTrace"] = True
        if self.streaming_configurations:
            invoke_params["streamingConfigurations"] = self.streaming_configurations

        # Override with any kwargs
        invoke_params.update(kwargs)

        response = self.client.invoke_agent(**invoke_params)

        # Stream completion chunks
        for event in response.get("completion", []):
            # Yield chunks
            if "chunk" in event:
                chunk_data = event["chunk"]
                if "bytes" in chunk_data:
                    text = chunk_data["bytes"].decode("utf-8")
                    if text:
                        yield text

            # Log trace output if enabled
            if "trace" in event and self.enable_trace:
                trace_event = event.get("trace")
                if trace_event:
                    trace = trace_event.get("trace", {})
                    for key, value in trace.items():
                        logger.info("%s: %s", key, value)
