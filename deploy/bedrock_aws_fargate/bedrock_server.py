"""
TAC Server with AWS Bedrock Agent Connector

Dependencies are managed via pyproject.toml.
Requires: tac-aws[server]>=0.1.0

Prerequisites:
- Deploy an agent to AWS Bedrock Agent
- Set required TAC environment variables (see README.md)
- Configure AWS credentials (IAM permission: bedrock:InvokeAgent)
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import boto3
from dotenv import load_dotenv
from tac import TAC
from tac.core.config import TACConfig
from tac.models.session import ConversationSession
from tac.server import TACFastAPIServer

from tac_aws.connectors import BedrockConnector

if TYPE_CHECKING:
    from mypy_boto3_bedrock_agent_runtime.type_defs import InvokeAgentResponseTypeDef

load_dotenv()

tac = TAC(config=TACConfig.from_env())

# Get Bedrock Agent configuration from environment
agent_id = os.getenv("BEDROCK_AGENT_ID")
agent_alias_id = os.getenv("BEDROCK_AGENT_ALIAS_ID", "TSTALIASID")
region = os.getenv("AWS_REGION", "us-east-1")

if not agent_id:
    raise ValueError(
        "BEDROCK_AGENT_ID environment variable is required. "
        "Set it to your Bedrock Agent ID"
    )

# Create Bedrock Agent Runtime client
bedrock_client = boto3.client("bedrock-agent-runtime", region_name=region)


def invoke_agent(
    context: ConversationSession,
    user_message: str,
    memory_context: str | None,
) -> InvokeAgentResponseTypeDef:
    """Invoke Bedrock Agent with full control over parameters."""
    full_message = user_message
    if memory_context:
        full_message = f"{memory_context}\n\nUser: {user_message}"

    return bedrock_client.invoke_agent(  # type: ignore[no-any-return]
        agentId=agent_id,
        agentAliasId=agent_alias_id,
        sessionId=context.conversation_id,
        inputText=full_message,
    )


# Create connector with invoke function
connector = BedrockConnector(tac=tac, invoke_fn=invoke_agent)

# TAC Server uses connector's channels for HTTP routing
server = TACFastAPIServer(tac=tac, voice_channel=connector.voice, sms_channel=connector.sms)

if __name__ == "__main__":
    server.start()
