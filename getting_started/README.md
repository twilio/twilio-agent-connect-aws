# Getting Started with TAC AWS

Quick start guide for using TAC AWS with AWS agent runtimes.

## Installation

### For Strands SDK

```bash
# With TAC server support
pip install tac-aws[strands,server]
```

### For Bedrock AgentCore

```bash
# With TAC server support
pip install tac-aws[agentcore,server]
```

### For Development

```bash
# Includes all connectors and development tools
pip install tac-aws[dev]
```

## Environment Setup

Create a `.env` file with your Twilio credentials:

```bash
# Twilio Configuration (required)
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_API_KEY=your_api_key
TWILIO_API_TOKEN=your_api_token
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_CONVERSATION_SERVICE_SID=conv_configuration_xxx

# Server Configuration (for Voice)
TWILIO_TAC_VOICE_PUBLIC_DOMAIN=your-domain.ngrok.io
```

## Examples

See [`examples/`](examples/) for complete working examples:

- `strands_agents.py` - Strands SDK with TAC Server
- `bedrock_agentcore_agents.py` - Bedrock AgentCore with TAC Server

## Quick Example

```python
from strands import Agent
from tac import TAC, TACConfig
from tac.models.session import ConversationSession
from tac.server import TACFastAPIServer
from tac_aws.connectors import StrandsConnector

# Create TAC instance
tac = TAC(config=TACConfig.from_env())

# Agent factory receives conversation context
def create_agent(context: ConversationSession) -> Agent:
    return Agent(
        model="amazon.nova-pro-v1:0",
        system_prompt="You are helpful."
    )

# Create connector (combines agent runtime + channel management)
connector = StrandsConnector(tac=tac, agent_factory=create_agent)

# TAC Server uses connector's channels for HTTP routing
server = TACFastAPIServer(tac=tac, voice_channel=connector.voice, sms_channel=connector.sms)
server.start()
```

Connectors handle:
- Multi-channel support (SMS + Voice)
- Memory retrieval and injection
- Conversation management
- Response routing
