"""
Example: OmniChannelFastAPIServer with Strands Adapter

This example shows how to use the adapter pattern with Strands SDK.
The adapter provides a clean interface for agent invocation.

Install dependencies:
    pip install tac[server] strands-agents
"""

import os

from dotenv import load_dotenv
from requests import session
from strands import Agent
from tac import TAC
from tac.channels import SMSChannel, VoiceChannel
from tac.core.config import TACConfig

from tac_aws.adapters import StrandsAdapter
from tac_aws.handlers import OmniChannelHandlers
from tac_aws.servers import OmniChannelFastAPIServer

load_dotenv()

# Step 1: Create TAC instance
tac = TAC(config=TACConfig.from_env())

# Step 2: Create your Strands agent
agent = Agent(
    model="amazon.nova-pro-v1:0",
    system_prompt="You are a helpful customer service agent. Be concise and friendly.",
)

# Step 3: Wrap it in the Strands adapter
adapter = StrandsAdapter(agent)

# Step 4: Create channel handlers (manages conversation logic)
handlers = OmniChannelHandlers(
    tac=tac,
    adapter=adapter,
    voice=VoiceChannel(tac=tac, auto_retrieve_memory=True),
    sms=SMSChannel(tac=tac, auto_retrieve_memory=True),
)

# Step 5: Create server (handles HTTP routing)
server = OmniChannelFastAPIServer(handlers=handlers)

if __name__ == "__main__":
    # Start the server!
    # OmniChannelFastAPIServer handles:
    # - Conversation history per conversation
    # - Memory retrieval and injection
    # - Agent invocation via adapter
    # - Response routing
    #
    # OmniChannelHandlers provides:
    # - Voice and SMS channel instances
    # - Channel lifecycle management
    #
    # StrandsAdapter handles:
    # - Strands-specific API calls
    # - Response formatting
    server.start()
