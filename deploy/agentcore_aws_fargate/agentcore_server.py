"""TAC Server with AWS Bedrock AgentCore Connector.

Demonstrates dual-runtime pattern:
- Voice: WebSocket streaming (~50ms latency)
- SMS: HTTP invocation (reliability and simplicity)

Prerequisites:
  pip install twilio-agent-connect-aws[agentcore,server]

Environment Variables:
  BEDROCK_AGENTCORE_AGENT_ARN: ARN of deployed AgentCore runtime
  AWS_REGION (optional): Defaults to us-east-1
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

import boto3
import websockets
from bedrock_agentcore.runtime import AgentCoreRuntimeClient
from dotenv import load_dotenv
from tac import TAC
from tac.channels.sms import SMSChannelConfig
from tac.channels.voice import VoiceChannelConfig
from tac.core.config import TACConfig
from tac.models.session import ConversationSession
from tac.session import ThreadSafeSessionManager

from tac_aws.connectors import BedrockAgentCoreConnector
from tac_aws.connectors.bedrock_agentcore.config import RuntimeConfig, WebSocketConfig
from tac_aws.server import TACAWSFastAPIServer

if TYPE_CHECKING:
    from mypy_boto3_bedrock_agentcore.type_defs import InvokeAgentRuntimeResponseTypeDef
    from websockets.client import WebSocketClientProtocol

load_dotenv()

# Initialize TAC
tac = TAC(config=TACConfig.from_env())

# Get AgentCore configuration
agent_arn = os.environ["BEDROCK_AGENTCORE_AGENT_ARN"]
region = os.getenv("AWS_REGION", "us-east-1")

# Voice: WebSocket (uses AgentCoreRuntimeClient for generate_ws_connection)
agentcore_client = AgentCoreRuntimeClient(region=region)


async def create_websocket(context: ConversationSession) -> WebSocketClientProtocol:
    """
    WebSocket factory for voice channel.

    Called once per session for connection pooling.
    Uses AgentCoreRuntimeClient to generate authenticated WebSocket URL.
    """
    ws_url, headers = agentcore_client.generate_ws_connection(
        runtime_arn=agent_arn,
        session_id=context.conversation_id,
    )
    ws = await websockets.connect(ws_url, extra_headers=headers)
    return ws


def build_websocket_payload(
    context: ConversationSession,
    user_message: str,
    memory_context: str | None,
) -> dict[str, Any]:
    """
    Build WebSocket message payload.

    Called for every message - user controls payload format.
    This example uses AgentCore's expected format with 'voicePrompt'.
    """
    payload: dict[str, Any] = {"type": "prompt", "voicePrompt": user_message}
    if memory_context:
        payload["memoryContext"] = memory_context
    return payload


# SMS: HTTP (uses boto3 client for invoke_agent_runtime)
agentcore_http_client = boto3.client("bedrock-agentcore", region_name=region)


def invoke_agent_http(
    context: ConversationSession,
    user_message: str,
    memory_context: str | None,
) -> InvokeAgentRuntimeResponseTypeDef:
    """
    HTTP invocation for both channels (required).

    Used for SMS channel and as fallback for voice channel.
    User controls all invoke_agent_runtime() parameters.
    """
    full_message = user_message
    if memory_context:
        full_message = f"{memory_context}\n\nUser: {user_message}"

    payload = json.dumps({"prompt": full_message}).encode("utf-8")

    response: InvokeAgentRuntimeResponseTypeDef = agentcore_http_client.invoke_agent_runtime(
        agentRuntimeArn=agent_arn,
        runtimeSessionId=context.conversation_id,
        payload=payload,
    )
    return response


# Create connector
connector = BedrockAgentCoreConnector(
    tac=tac,
    runtime=RuntimeConfig(
        http=invoke_agent_http,  # Required: HTTP streaming for both channels
        websocket=WebSocketConfig(  # Optional: WebSocket optimization for voice
            factory=create_websocket,
            payload_fn=build_websocket_payload,
        ),
    ),
    voice_config=VoiceChannelConfig(
        session_manager=ThreadSafeSessionManager(),
        memory_mode="always",
    ),
    sms_config=SMSChannelConfig(memory_mode="always"),
)

# Create server
server = TACAWSFastAPIServer(
    tac=tac, voice_channel=connector.voice, messaging_channels=[connector.sms]
)

if __name__ == "__main__":
    server.start()
