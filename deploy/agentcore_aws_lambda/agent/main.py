"""
TAC Agent for AWS Bedrock AgentCore with Strands AI
Simplified using StrandsConnector and TACAWSBedrockAgentCoreServer
"""

import json

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel
from strands.session import FileSessionManager
from tac import TAC
from tac.channels.sms import SMSChannelConfig
from tac.channels.voice import VoiceChannelConfig
from tac.core.logging import get_logger
from tac.models.session import ConversationSession
from tac_config import create_tac_config

from tac_aws.connectors import StrandsConnector

logger = get_logger(__name__)

# Initialize TAC with credentials from Secrets Manager
tac = TAC(config=create_tac_config())


def create_agent(context: ConversationSession) -> Agent:
    """
    Agent factory for Strands connector.

    Called once per conversation to create an isolated agent instance.
    Uses FileSessionManager to persist conversation history across microVM shutdowns.

    See:
    - Strands Session Management: https://strandsagents.com/docs/user-guide/concepts/agents/session-management/
    - AgentCore Managed Session Storage: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-filesystem-configurations.html
    """
    return Agent(
        model=BedrockModel(model_id="amazon.nova-pro-v1:0"),
        system_prompt="You are a helpful customer service agent. Keep responses short and conversational — one or two sentences. Do not use markdown, asterisks, bullets, or emojis.",
        session_manager=FileSessionManager(
            session_id=context.conversation_id, storage_dir="/mnt/workspace/.sessions"
        ),
    )


# Create Strands connector
connector = StrandsConnector(
    tac=tac,
    agent_factory=create_agent,
    voice_config=VoiceChannelConfig(memory_mode="once"),
    sms_config=SMSChannelConfig(memory_mode="always"),
)


class WelcomeGreetingWebSocket:
    """
    WebSocket wrapper that sends a welcome greeting after setup.

    Required for Twilio ConversationRelay with conversationConfiguration.
    Without an initial greeting, ConversationRelay won't activate speech detection.
    """

    def __init__(self, ws):
        self._ws = ws
        self._setup_received = False

    async def receive_json(self):
        data = await self._ws.receive_json()

        if not self._setup_received and data.get("type") == "setup":
            self._setup_received = True
            try:
                welcome_msg = {
                    "type": "text",
                    "token": "Hello! How can I assist you today?",
                    "last": True,
                }
                await self._ws.send_text(json.dumps(welcome_msg))
            except Exception as e:
                logger.error(f"Failed to send welcome greeting: {e}")

        return data

    async def send_text(self, data: str):
        return await self._ws.send_text(data)

    async def close(self):
        return await self._ws.close()

    def __getattr__(self, name):
        return getattr(self._ws, name)


class TACBedrockAgentCoreApp:
    """
    App adapter for TAC on AWS Bedrock AgentCore.

    Integrates TAC channels with BedrockAgentCoreApp for serverless deployment.
    Handles both HTTP (SMS) and WebSocket (Voice) protocols.
    """

    def __init__(self, tac: TAC, voice_channel, sms_channel):
        self.tac = tac
        self.voice_channel = voice_channel
        self.sms_channel = sms_channel
        self.app = BedrockAgentCoreApp()

        # Register HTTP entrypoint for SMS
        @self.app.entrypoint
        async def http_handler(payload):
            try:
                webhook_data = json.loads(payload.get("webhook_data", "{}"))
                idempotency_token = payload.get("idempotency_token")

                await self.sms_channel.process_webhook(webhook_data, idempotency_token)
                return {"status": "ok"}

            except Exception as e:
                logger.error(f"Error processing SMS webhook: {e}", exc_info=True)
                return {"status": "error", "message": str(e)}

        # Register WebSocket entrypoint for Voice
        @self.app.websocket
        async def websocket_handler(websocket, context):
            # TODO: Add Twilio webhook signature validation
            # Conversation Relay includes X-Twilio-Signature header in the initial
            # WebSocket handshake request. We should validate this signature using the
            # Twilio auth token to ensure requests are genuinely from Twilio.
            # See: https://www.twilio.com/docs/voice/conversationrelay/onboarding
            # Note: Currently blocked because AgentCore strips headers from WebSocket requests.
            # This security enhancement should be implemented once AgentCore supports
            # passing handshake headers to the WebSocket handler.
            try:
                wrapped_ws = WelcomeGreetingWebSocket(websocket)
                await self.voice_channel.handle_websocket(wrapped_ws)

            except Exception as e:
                logger.error(f"Error in WebSocket handler: {e}", exc_info=True)
                try:
                    await websocket.close()
                except Exception:
                    pass

    def run(self):
        """Start the AgentCore app."""
        self.app.run()


# Create app
tac_app = TACBedrockAgentCoreApp(
    tac=tac,
    voice_channel=connector.voice,
    sms_channel=connector.sms,
)

# For AgentCore deployment
app = tac_app.app

if __name__ == "__main__":
    tac_app.run()
