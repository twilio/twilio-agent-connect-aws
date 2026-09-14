"""
TAC Server with AWS Bedrock Agent Connector

Prerequisites:
    pip install twilio-agent-connect-aws[bedrock,server]

Environment Variables:
    BEDROCK_AGENT_ID - Bedrock Agent ID
    BEDROCK_AGENT_ALIAS_ID - Bedrock Agent Alias ID (default: TSTALIASID)
    AWS_REGION - AWS Region (default: us-east-1)
    TWILIO_VOICE_PUBLIC_DOMAIN - (Optional) Public domain for AWS ALB deployments with ngrok
"""

from __future__ import annotations

import os

import boto3
from dotenv import load_dotenv
from tac import TAC
from tac.channels.sms import SMSChannelConfig
from tac.channels.voice import VoiceChannelConfig
from tac.core.config import TACConfig
from tac.models.voice import TwiMLOptions

from tac_aws.connectors import BedrockConnector
from tac_aws.server import TACAWSFastAPIServer

load_dotenv()

tac = TAC(config=TACConfig.from_env())

agent_id = os.getenv("BEDROCK_AGENT_ID")
agent_alias_id = os.getenv("BEDROCK_AGENT_ALIAS_ID", "TSTALIASID")
region = os.getenv("AWS_REGION", "us-east-1")

if not agent_id:
    raise ValueError("BEDROCK_AGENT_ID environment variable is required")

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
    voice_config=VoiceChannelConfig(
        # Fetched once at call start and cached; "always" adds per-turn latency.
        memory_mode="once",
        # ConversationRelay TwiML customization. Every <ConversationRelay>
        # attribute is available here (voice, language, interruptible, ...);
        # for per-call overrides use connector.voice.on_inbound_call_twiml().
        default_twiml_options=TwiMLOptions(welcome_greeting="Hi! How can I help you today?"),
    ),
    sms_config=SMSChannelConfig(memory_mode="always"),
)

server = TACAWSFastAPIServer(
    tac=tac,
    voice_channel=connector.voice,
    # Every messaging channel available to the connector (SMS and Chat, plus RCS
    # and WhatsApp once their sender is set in the environment).
    messaging_channels=connector.channels.messaging,
)

if __name__ == "__main__":
    server.start()
