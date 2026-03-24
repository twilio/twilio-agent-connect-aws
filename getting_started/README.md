# Getting Started with TAC AWS

Quick start guide for using TAC AWS with AWS agent runtimes.

## Installation

```bash
# For FastAPI server
pip install tac-aws[server] strands-agents

# For development (includes all AWS SDKs)
pip install tac-aws[dev]
```

## Environment Setup

Create a `.env` file with your Twilio credentials:

```bash
# Twilio Configuration (required)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_API_KEY=your_api_key
TWILIO_API_TOKEN=your_api_token
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_CONVERSATION_SERVICE_SID=conv_configuration_xxx

# Server Configuration (for Voice)
TWILIO_TAC_VOICE_PUBLIC_DOMAIN=your-domain.ngrok.io
```

## Examples

See [`examples/`](examples/) for complete working example:

- `strands_agents.py` - Strands SDK with TAC Server

## Quick Example

```python
from strands import Agent
from tac import TAC, TACConfig
from tac.server import TACFastAPIServer
from tac_aws.adapters import StrandsAdapter
from tac_aws.handlers import OmniChannelHandler

# Create TAC instance
tac = TAC(config=TACConfig.from_env())

# Create agent factory and adapter
def create_agent() -> Agent:
    return Agent(model="amazon.nova-pro-v1:0", system_prompt="You are helpful.")

adapter = StrandsAdapter(agent_factory=create_agent)

# Create channel handler
handler = OmniChannelHandler(tac=tac, adapter=adapter)

# TAC Server uses handler's channels for HTTP routing
server = TACFastAPIServer(tac=tac, voice_channel=handler.voice, sms_channel=handler.sms)
server.start()
```

That's it! TAC AWS handles:
- Multi-channel support (SMS + Voice)
- Memory retrieval and injection
- Conversation history management
- Response routing
