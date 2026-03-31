"""
TAC Server with Bedrock AgentCore Connector

Dependencies are managed via pyproject.toml.
Requires: tac-aws[server]>=0.1.0
"""

import json
import os

import boto3
from dotenv import load_dotenv
from mypy_boto3_bedrock_agentcore.client import BedrockAgentCoreClient
from mypy_boto3_bedrock_agentcore.type_defs import InvokeAgentRuntimeResponseTypeDef
from tac import TAC
from tac.core.config import TACConfig
from tac.models.session import ConversationSession
from tac.server import TACFastAPIServer

from tac_aws.connectors import BedrockAgentCoreConnector

load_dotenv()

tac = TAC(config=TACConfig.from_env())

# Get AgentCore agent ARN from environment
agent_arn = os.getenv("BEDROCK_AGENTCORE_AGENT_ARN")
if not agent_arn:
    raise ValueError(
        "BEDROCK_AGENTCORE_AGENT_ARN environment variable is required. "
        "Set it to your deployed agent ARN (e.g., arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/agent-xxx)"
    )

# Create Bedrock AgentCore client
region = os.getenv("AWS_REGION", "us-east-1")
agentcore_client: BedrockAgentCoreClient = boto3.client("bedrock-agentcore", region_name=region)


def invoke_agent(
    context: ConversationSession,
    user_message: str,
    memory_context: str | None,
) -> InvokeAgentRuntimeResponseTypeDef:
    """Invoke agent with full control over parameters."""
    full_prompt = user_message
    if memory_context:
        full_prompt = f"{memory_context}\n\nUser: {user_message}"

    payload = json.dumps({"prompt": full_prompt}).encode("utf-8")

    return agentcore_client.invoke_agent_runtime(
        agentRuntimeArn=agent_arn,
        runtimeSessionId=context.conversation_id,
        payload=payload,
    )


# Connector invokes AgentCore runtime
connector = BedrockAgentCoreConnector(tac=tac, invoke_fn=invoke_agent)

# TAC Server uses connector's channels for HTTP routing
server = TACFastAPIServer(tac=tac, voice_channel=connector.voice, sms_channel=connector.sms)

if __name__ == "__main__":
    server.start()
