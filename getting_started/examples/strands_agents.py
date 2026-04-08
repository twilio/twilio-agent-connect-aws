"""
TAC Server with AWS Strands Connector

Prerequisites:
    pip install tac-aws[strands,server]
"""

from dotenv import load_dotenv
from strands import Agent
from tac import TAC
from tac.core.config import TACConfig
from tac.models.session import ConversationSession
from tac.server import TACFastAPIServer

from tac_aws.connectors import StrandsConnector

load_dotenv()

tac = TAC(config=TACConfig.from_env())


def create_agent(context: ConversationSession) -> Agent:
    return Agent(
        model="amazon.nova-pro-v1:0",
        system_prompt="You are a helpful assistant. Be concise and friendly.",
    )


connector = StrandsConnector(tac=tac, agent_factory=create_agent)
server = TACFastAPIServer(tac=tac, voice_channel=connector.voice, messaging_channels=[connector.sms])

if __name__ == "__main__":
    server.start()
