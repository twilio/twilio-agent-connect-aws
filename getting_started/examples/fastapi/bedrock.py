"""
Example: OmniChannelFastAPIServer with AWS Bedrock Adapter

This example shows how to use the adapter pattern with AWS Bedrock Agent Runtime.
The adapter provides a unified interface regardless of the underlying agent SDK.

Install dependencies:
    pip install tac[server] boto3
"""

import os

import boto3  # type: ignore[import-untyped]
from dotenv import load_dotenv
from tac import TAC
from tac.channels import SMSChannel, VoiceChannel
from tac.core.config import TACConfig

from tac_aws.adapters import BedrockAdapter
from tac_aws.handlers import OmniChannelHandlers
from tac_aws.servers import OmniChannelFastAPIServer

load_dotenv()

# Step 1: Create TAC instance
tac = TAC(config=TACConfig.from_env())

# Step 2: Create AWS Bedrock client
bedrock_client = boto3.client(
    "bedrock-agent-runtime",
    region_name=os.environ.get("AWS_REGION", "us-east-1"),
)

# Step 3: Wrap it in the Bedrock adapter
adapter = BedrockAdapter(
    client=bedrock_client,
    agent_id=os.environ["BEDROCK_AGENT_ID"],
    agent_alias_id=os.environ.get("BEDROCK_AGENT_ALIAS_ID", "TSTALIASID"),
    enable_trace=True,  # Enable trace logging
    streaming_configurations={
        "applyGuardrailInterval": 20,
        "streamFinalResponse": False,
    },
)

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
    # The adapter pattern allows you to swap out the underlying agent runtime
    # without changing any other code. Just swap StrandsAdapter for BedrockAdapter!
    #
    # Benefits:
    # - Unified interface across different agent SDKs
    # - Easy to test with mock adapters
    # - Clean separation of concerns
    # - Simple to add new agent runtimes
    server.start()
