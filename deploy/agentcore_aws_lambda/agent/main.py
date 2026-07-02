"""
TAC Agent for AWS Bedrock AgentCore with Strands AI
Simplified using StrandsConnector and TACAWSBedrockAgentCoreServer
"""

from strands import Agent
from strands.models import BedrockModel
from strands.session import FileSessionManager
from tac import TAC
from tac.channels.sms import SMSChannelConfig
from tac.channels.voice import VoiceChannelConfig
from tac.models.session import ConversationSession
from tac_config import create_tac_config

from tac_aws.connectors import StrandsConnector
from tac_aws.server import TACAgentCoreApp

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

# Create app
tac_app = TACAgentCoreApp(
    tac=tac,
    voice_channel=connector.voice,
    sms_channel=connector.sms,
)

# For AgentCore deployment
app = tac_app.app

if __name__ == "__main__":
    tac_app.run()
