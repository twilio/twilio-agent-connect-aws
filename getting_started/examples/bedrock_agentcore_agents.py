"""
TAC Server with Bedrock Agent Core Connector

Install: pip install tac[server] tac-aws boto3

Prerequisites:
- Deploy an agent to AWS Bedrock Agent Core
- Set required TAC environment variables (see README.md)
- Configure AWS credentials (IAM permission: bedrock-agentcore:InvokeAgentRuntime)
"""

import json

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

# Create Bedrock Agent Core client
agentcore_client: BedrockAgentCoreClient = boto3.client("bedrock-agentcore", region_name="us-east-1")

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
        agentRuntimeArn="arn:aws:bedrock-agentcore:us-east-1:123456789012:agent-runtime/YOUR_RUNTIME_ID",
        runtimeSessionId=context.conversation_id,
        payload=payload,
    )


# Create connector with your invoke function
connector = BedrockAgentCoreConnector(tac=tac, invoke_fn=invoke_agent)

# TAC Server uses connector's channels for HTTP routing
server = TACFastAPIServer(tac=tac, voice_channel=connector.voice, sms_channel=connector.sms)

if __name__ == "__main__":
    server.start()
