"""
Example: OmniChannelFastAPIServer with AWS Bedrock AgentCore Adapter

This example shows how to use the adapter pattern with AWS Bedrock AgentCore service.
AgentCore is a newer service compared to Bedrock Agent Runtime.

Install dependencies:
    pip install tac-aws[server] boto3
"""

import os

import boto3  # type: ignore[import-untyped]
from dotenv import load_dotenv
from tac import TAC
from tac.channels import SMSChannel, VoiceChannel
from tac.core.config import TACConfig

from tac_aws.adapters import BedrockAgentCoreAdapter
from tac_aws.handlers import OmniChannelHandlers
from tac_aws.servers import OmniChannelFastAPIServer

load_dotenv()

# Step 1: Create TAC instance
tac = TAC(config=TACConfig.from_env())

# Step 2: Create AWS Bedrock AgentCore client
agentcore_client = boto3.client(
    "bedrock-agentcore",
    region_name=os.environ.get("AWS_REGION", "us-east-1"),
)

# Step 3: Wrap it in the AgentCore adapter
adapter = BedrockAgentCoreAdapter(
    client=agentcore_client,
    agent_runtime_arn=os.environ["BEDROCK_AGENTCORE_ARN"],
    qualifier=os.environ.get("BEDROCK_AGENTCORE_QUALIFIER", "DEFAULT"),
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
    # The adapter pattern allows you to swap between different AWS agent services:
    # - StrandsAdapter for AWS Strands SDK
    # - BedrockAdapter for Bedrock Agent Runtime
    # - BedrockAgentCoreAdapter for Bedrock AgentCore (this example)
    #
    # Benefits:
    # - Unified interface across different agent services
    # - Easy to switch between services
    # - Clean separation of concerns
    # - Simple to add new agent runtimes
    server.start()
