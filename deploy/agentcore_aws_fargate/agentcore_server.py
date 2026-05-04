"""
TAC Server with Bedrock AgentCore Connector (Dual Runtime: HTTP + WebSocket)

Dependencies are managed via pyproject.toml.
Requires: aws-twilio-agent-connect[server]>=0.1.0, bedrock-agentcore>=1.4.8

This server demonstrates the dual-runtime pattern:
- HTTP: Required for both voice and SMS (fallback for voice, primary for SMS)
- WebSocket: Optional for voice channel low-latency streaming (~50ms vs ~200ms)
"""

import json
import os
from typing import TYPE_CHECKING, Any

import boto3
import websockets
from bedrock_agentcore.runtime import AgentCoreRuntimeClient
from dotenv import load_dotenv
from tac import TAC
from tac.channels.voice import VoiceChannelConfig
from tac.core.config import TACConfig
from tac.models.session import ConversationSession
from tac.server import TACFastAPIServer
from tac.session import ThreadSafeSessionManager

from tac_aws.connectors import BedrockAgentCoreConnector
from tac_aws.connectors.bedrock_agentcore.config import RuntimeConfig, WebSocketConfig

if TYPE_CHECKING:
    from mypy_boto3_bedrock_agentcore.client import BedrockAgentCoreClient
    from mypy_boto3_bedrock_agentcore.type_defs import InvokeAgentRuntimeResponseTypeDef
    from websockets.client import WebSocketClientProtocol

load_dotenv()

# Initialize TAC
tac = TAC(config=TACConfig.from_env())

# Get AgentCore agent ARN from environment
agent_arn = os.getenv("BEDROCK_AGENTCORE_AGENT_ARN")
if not agent_arn:
    raise ValueError(
        "BEDROCK_AGENTCORE_AGENT_ARN environment variable is required. "
        "Set it to your deployed agent ARN (e.g., arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/agent-xxx)"
    )

# AWS Configuration
region = os.getenv("AWS_REGION", "us-east-1")

# ═══════════════════════════════════════════════════════════════
# 1. WebSocket Configuration (Low-Latency Voice Optimization)
# ═══════════════════════════════════════════════════════════════
agentcore_runtime_client = AgentCoreRuntimeClient(region=region)


async def create_websocket(context: ConversationSession) -> "WebSocketClientProtocol":
    """Create WebSocket connection for low-latency streaming.

    Called once per session and reused via connection pooling in the connector.
    """
    ws_url, headers = agentcore_runtime_client.generate_ws_connection(
        runtime_arn=agent_arn,
        session_id=context.conversation_id,
    )
    ws = await websockets.connect(ws_url, additional_headers=headers)
    return ws


def build_websocket_payload(
    context: ConversationSession,
    user_message: str,
    memory_context: str | None,
) -> dict[str, Any]:
    """Build WebSocket message payload.

    Called for every message sent via WebSocket.
    """
    payload: dict[str, Any] = {
        "type": "prompt",
        "voicePrompt": user_message,
    }
    if memory_context:
        payload["memoryContext"] = memory_context
    return payload


# ═══════════════════════════════════════════════════════════════
# 2. HTTP Configuration (Required for SMS, Fallback for Voice)
# ═══════════════════════════════════════════════════════════════
agentcore_http_client = boto3.client("bedrock-agentcore", region_name=region)


def invoke_agent_http(
    context: ConversationSession,
    user_message: str,
    memory_context: str | None,
) -> "InvokeAgentRuntimeResponseTypeDef":
    """HTTP invocation for SMS channel and voice fallback.

    Returns streaming response that will be parsed by the connector.
    """
    full_prompt = user_message
    if memory_context:
        full_prompt = f"{memory_context}\n\nUser: {user_message}"

    payload = json.dumps({"prompt": full_prompt}).encode("utf-8")

    return agentcore_http_client.invoke_agent_runtime(
        agentRuntimeArn=agent_arn,
        runtimeSessionId=context.conversation_id,
        payload=payload,
    )


# ═══════════════════════════════════════════════════════════════
# 3. Create Connector with Dual Runtime Configuration
# ═══════════════════════════════════════════════════════════════
connector = BedrockAgentCoreConnector(
    tac=tac,
    runtime=RuntimeConfig(
        http=invoke_agent_http,  # Required: HTTP streaming
        websocket=WebSocketConfig(  # Optional: Low-latency WebSocket streaming
            factory=create_websocket,
            payload_fn=build_websocket_payload,
        ),
    ),
    voice_config=VoiceChannelConfig(
        session_manager=ThreadSafeSessionManager(),
        auto_retrieve_memory=True,  # Automatically fetch memory context
    ),
)

# ═══════════════════════════════════════════════════════════════
# 4. Start TAC FastAPI Server
# ═══════════════════════════════════════════════════════════════
server = TACFastAPIServer(
    tac=tac,
    voice_channel=connector.voice,
    messaging_channels=[connector.sms],
)

if __name__ == "__main__":
    server.start()
