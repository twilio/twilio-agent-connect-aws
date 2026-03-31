"""
TAC Server with AWS Bedrock AgentCore Connector

Prerequisites:
    pip install tac-aws[agentcore,server]

Environment Variables:
    BEDROCK_AGENTCORE_AGENT_ARN - AgentCore runtime ARN
    AWS_REGION - AWS Region (default: us-east-1)
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

import boto3
from dotenv import load_dotenv
from tac import TAC
from tac.core.config import TACConfig
from tac.models.session import ConversationSession
from tac.server import TACFastAPIServer

from tac_aws.connectors import BedrockAgentCoreConnector

if TYPE_CHECKING:
    from mypy_boto3_bedrock_agentcore.type_defs import InvokeAgentRuntimeResponseTypeDef

load_dotenv()

tac = TAC(config=TACConfig.from_env())

agent_arn = os.getenv("BEDROCK_AGENTCORE_AGENT_ARN")
region = os.getenv("AWS_REGION", "us-east-1")

if not agent_arn:
    raise ValueError("BEDROCK_AGENTCORE_AGENT_ARN environment variable is required")

agentcore_client = boto3.client("bedrock-agentcore", region_name=region)


def invoke_agent(
    context: ConversationSession,
    user_message: str,
    memory_context: str | None,
) -> InvokeAgentRuntimeResponseTypeDef:
    full_message = user_message
    if memory_context:
        full_message = f"{memory_context}\n\nUser: {user_message}"

    payload = json.dumps({"prompt": full_message}).encode("utf-8")

    return agentcore_client.invoke_agent_runtime(  # type: ignore[no-any-return]
        agentRuntimeArn=agent_arn,
        runtimeSessionId=context.conversation_id,
        payload=payload,
    )


connector = BedrockAgentCoreConnector(tac=tac, invoke_fn=invoke_agent)
server = TACFastAPIServer(tac=tac, voice_channel=connector.voice, sms_channel=connector.sms)

if __name__ == "__main__":
    server.start()
