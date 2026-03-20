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

See [`examples/fastapi/`](examples/fastapi/) for complete working examples:

- `strands_agents.py` - Strands SDK with FastAPI server
- `bedrock.py` - Bedrock Agent Runtime with FastAPI server
- `bedrock_agentcore.py` - Bedrock AgentCore with FastAPI server

## Quick Example

```python
from strands import Agent
from tac import TAC, TACConfig
from tac.channels import SMSChannel, VoiceChannel
from tac_aws.adapters import StrandsAdapter
from tac_aws.handlers import OmniChannelHandlers
from tac_aws.servers import OmniChannelFastAPIServer

# Create TAC instance
tac = TAC(config=TACConfig.from_env())

# Create agent and wrap in adapter
agent = Agent(model="gpt-4o")
adapter = StrandsAdapter(agent)

# Create channel handlers
handlers = OmniChannelHandlers(
    tac=tac,
    adapter=adapter,
    voice=VoiceChannel(tac=tac, auto_retrieve_memory=True),
    sms=SMSChannel(tac=tac, auto_retrieve_memory=True),
)

# Create and start server
server = OmniChannelFastAPIServer(handlers=handlers)
server.start()
```

That's it! TAC AWS handles:
- Multi-channel support (SMS + Voice)
- Memory retrieval and injection
- Conversation history management
- Response routing
