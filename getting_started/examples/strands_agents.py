"""
TAC Server with AWS Strands Connector

Prerequisites:
    pip install twilio-agent-connect-aws[strands,server]
"""

from dotenv import load_dotenv
from strands import Agent
from tac import TAC
from tac.channels.sms import SMSChannelConfig
from tac.channels.voice import VoiceChannelConfig
from tac.core.config import TACConfig
from tac.models.session import ConversationSession
from tac.models.voice import TwiMLOptions

from tac_aws.connectors import StrandsConnector
from tac_aws.server import TACAWSFastAPIServer

load_dotenv()

tac = TAC(config=TACConfig.from_env())


def create_agent(context: ConversationSession) -> Agent:
    return Agent(
        model="amazon.nova-pro-v1:0",
        system_prompt="You are a helpful assistant. Be concise and friendly.",
    )


connector = StrandsConnector(
    tac=tac,
    agent_factory=create_agent,
    voice_config=VoiceChannelConfig(
        # Voice fetches memory once at call start and caches it — a
        # per-turn fetch ("always") adds latency to every response.
        memory_mode="once",
        # ConversationRelay TwiML customization. Every <ConversationRelay>
        # attribute is available here (voice, language, interruptible, ...);
        # for per-call overrides use connector.voice.on_inbound_call_twiml().
        default_twiml_options=TwiMLOptions(welcome_greeting="Hi! How can I help you today?"),
    ),
    sms_config=SMSChannelConfig(memory_mode="always"),
)

server = TACAWSFastAPIServer(
    tac=tac,
    voice_channel=connector.voice,
    # Every messaging channel the connector enabled (SMS here; add rcs_config /
    # whatsapp_config / chat_config above to enable more).
    messaging_channels=connector.channels.messaging,
)

if __name__ == "__main__":
    server.start()
