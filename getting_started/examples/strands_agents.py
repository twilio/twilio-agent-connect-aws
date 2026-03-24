"""
TAC Server with Strands Adapter

Install: pip install tac[server] strands-agents
"""

from dotenv import load_dotenv
from strands import Agent
from tac import TAC
from tac.core.config import TACConfig
from tac.server import TACFastAPIServer

from tac_aws.adapters import StrandsAdapter
from tac_aws.handlers import OmniChannelHandler

load_dotenv()

tac = TAC(config=TACConfig.from_env())


def create_agent() -> Agent:
    """Factory creates one agent per conversation."""
    return Agent(
        model="amazon.nova-pro-v1:0",
        system_prompt=(
            "You are a helpful assistant. Remember everything the user tells you "
            "in this conversation and refer back to it when asked. Be concise and friendly."
        ),
    )


adapter = StrandsAdapter(agent_factory=create_agent)

# Handler creates channels and registers message processing
handler = OmniChannelHandler(tac=tac, adapter=adapter)

# TAC Server uses handler's channels for HTTP routing
server = TACFastAPIServer(tac=tac, voice_channel=handler.voice, sms_channel=handler.sms)

if __name__ == "__main__":
    server.start()
