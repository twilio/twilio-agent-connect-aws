"""AWS Bedrock AgentCore adapter."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from tac_aws.adapters.base import BaseAgentAdapter

if TYPE_CHECKING:
    from mypy_boto3_bedrock_agentcore.client import BedrockAgentCoreClient


class BedrockAgentCoreAdapter(BaseAgentAdapter):
    """Adapter for AWS Bedrock AgentCore service."""

    def __init__(
        self,
        client: BedrockAgentCoreClient,
        agent_runtime_arn: str,
        qualifier: str = "DEFAULT",
    ) -> None:
        """
        Initialize Bedrock AgentCore adapter.

        Args:
            client: boto3 bedrock-agentcore client
            agent_runtime_arn: Agent Runtime ARN
            qualifier: Agent qualifier (default: DEFAULT)
        """
        self.client: BedrockAgentCoreClient = client
        self.agent_runtime_arn = agent_runtime_arn
        self.qualifier = qualifier

    async def run_async(self, message: str, session_id: str, **kwargs: Any) -> str:
        """
        Run Bedrock AgentCore agent asynchronously.

        Args:
            message: Input text
            session_id: Session ID for conversation state
            **kwargs: Additional parameters for invoke_agent_runtime()

        Returns:
            Complete response text from agent
        """
        # Prepare payload
        payload = json.dumps({"prompt": message}).encode()

        invoke_params: dict[str, Any] = {
            "agentRuntimeArn": self.agent_runtime_arn,
            "runtimeSessionId": session_id,
            "payload": payload,
            "qualifier": self.qualifier,
        }

        # Override with any kwargs
        invoke_params.update(kwargs)

        response = self.client.invoke_agent_runtime(**invoke_params)

        # Collect response chunks
        content = []
        for chunk in response.get("response", []):
            content.append(chunk.decode("utf-8"))

        # Parse JSON response
        if content:
            response_data = json.loads("".join(content))
            # Extract text from response (structure may vary)
            if isinstance(response_data, dict):
                return str(response_data.get("response", response_data))
            return str(response_data)

        return ""

    async def stream_async(
        self, message: str, session_id: str, **kwargs: Any
    ) -> AsyncIterator[str]:
        """
        Run Bedrock AgentCore agent with streaming.

        Args:
            message: Input text
            session_id: Session ID for conversation state
            **kwargs: Additional parameters for invoke_agent_runtime()

        Yields:
            Response text chunks
        """
        # Prepare payload
        payload = json.dumps({"prompt": message}).encode()

        invoke_params: dict[str, Any] = {
            "agentRuntimeArn": self.agent_runtime_arn,
            "runtimeSessionId": session_id,
            "payload": payload,
            "qualifier": self.qualifier,
        }

        # Override with any kwargs
        invoke_params.update(kwargs)

        response = self.client.invoke_agent_runtime(**invoke_params)

        # Stream response chunks
        for chunk in response.get("response", []):
            decoded = chunk.decode("utf-8")
            if decoded:
                yield decoded
