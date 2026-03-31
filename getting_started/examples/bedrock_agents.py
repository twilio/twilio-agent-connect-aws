"""
TAC Server with AWS Bedrock Agent Connector

Prerequisites:
    pip install tac-aws[bedrock,server]

Environment Variables:
    BEDROCK_AGENT_ID - Bedrock Agent ID
    BEDROCK_AGENT_ALIAS_ID - Bedrock Agent Alias ID (default: TSTALIASID)
    AWS_REGION - AWS Region (default: us-east-1)
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

agent_id = os.getenv("BEDROCK_AGENT_ID")
agent_alias_id = os.getenv("BEDROCK_AGENT_ALIAS_ID", "TSTALIASID")
region = os.getenv("AWS_REGION", "us-east-1")

if not agent_id:
    raise ValueError("BEDROCK_AGENT_ID environment variable is required")

bedrock_client = boto3.client("bedrock-agent-runtime", region_name=region)


def invoke_agent(
    context: ConversationSession,
    user_message: str,
    memory_context: str | None,
) -> InvokeAgentResponseTypeDef:
    full_message = user_message
    if memory_context:
        full_message = f"{memory_context}\n\nUser: {user_message}"

    return bedrock_client.invoke_agent(  # type: ignore[no-any-return]
        agentId=agent_id,
        agentAliasId=agent_alias_id,
        sessionId=context.conversation_id,
        inputText=full_message,
    )


connector = BedrockConnector(tac=tac, invoke_fn=invoke_agent)
server = TACFastAPIServer(tac=tac, voice_channel=connector.voice, sms_channel=connector.sms)

if __name__ == "__main__":
    server.start()
