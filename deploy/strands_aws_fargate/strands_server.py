"""
TAC Server with Strands Connector

Dependencies are managed via pyproject.toml.
Requires aws-twilio-agent-connect[strands,server] version 0.1.0 or later.
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
    """
    Factory creates one agent per conversation.

    Receives conversation context to enable SessionManager and context-aware configuration.

    Args:
        context: ConversationSession with conversation_id, channel, customer_id, etc.
    """
    return Agent(
        model="us.amazon.nova-pro-v1:0",  # Use cross-region inference profile
        system_prompt=(
            "You are a helpful assistant. Remember everything the user tells you "
            "in this conversation and refer back to it when asked. Be concise and friendly."
        ),
    )


# Connector creates channels and registers message processing
connector = StrandsConnector(tac=tac, agent_factory=create_agent)

# TAC Server uses connector's channels for HTTP routing
server = TACFastAPIServer(
    tac=tac, voice_channel=connector.voice, messaging_channels=[connector.sms]
)

if __name__ == "__main__":
    server.start()
