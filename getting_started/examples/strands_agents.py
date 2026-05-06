"""
TAC Server with AWS Strands Connector

Prerequisites:
    pip install twilio-agent-connect-aws[strands,server]
"""

from dotenv import load_dotenv
from strands import Agent
from tac import TAC
from tac.channels.sms import SMSChannelConfig
from tac.channels.voice import VoiceChannelConfig
from tac.core.config import TACConfig
from tac.models.session import ConversationSession

from tac_aws.connectors import StrandsConnector
from tac_aws.server import TACAWSFastAPIServer

load_dotenv()

tac = TAC(config=TACConfig.from_env())


def create_agent(context: ConversationSession) -> Agent:
    return Agent(
        model="amazon.nova-pro-v1:0",
        system_prompt="You are a helpful assistant. Be concise and friendly.",
    )


connector = StrandsConnector(
    tac=tac,
    agent_factory=create_agent,
    voice_config=VoiceChannelConfig(memory_mode="always"),
    sms_config=SMSChannelConfig(memory_mode="always"),
)

server = TACAWSFastAPIServer(
    tac=tac, voice_channel=connector.voice, messaging_channels=[connector.sms]
)

if __name__ == "__main__":
    server.start()
