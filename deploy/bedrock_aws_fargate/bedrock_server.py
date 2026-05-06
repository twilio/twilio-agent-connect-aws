"""
TAC Server with AWS Bedrock Agent Connector

Dependencies are managed via pyproject.toml.
Requires twilio-agent-connect-aws[bedrock,server] version 1.0.0 or later.

Prerequisites:
- Deploy an agent to AWS Bedrock Agent
- Set required TAC environment variables (see README.md)
- Configure AWS credentials (IAM permission: bedrock:InvokeAgent)
"""

from __future__ import annotations

import os

import boto3
from dotenv import load_dotenv
from tac import TAC
from tac.channels.sms import SMSChannelConfig
from tac.channels.voice import VoiceChannelConfig
from tac.core.config import TACConfig

from tac_aws.connectors import BedrockConnector
from tac_aws.server import TACAWSFastAPIServer

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

# Simple config-based approach (recommended)
# sessionId and inputText are auto-injected by the connector
connector = BedrockConnector(
    tac=tac,
    bedrock_client=bedrock_client,
    config={
        "agentId": agent_id,
        "agentAliasId": agent_alias_id,
    },
    voice_config=VoiceChannelConfig(memory_mode="always"),
    sms_config=SMSChannelConfig(memory_mode="always"),
)

server = TACAWSFastAPIServer(
    tac=tac, voice_channel=connector.voice, messaging_channels=[connector.sms]
)

if __name__ == "__main__":
    server.start()
