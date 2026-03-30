# TAC AWS - AWS Integrations for Twilio Agent Connect

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AWS-specific connectors for [Twilio Agent Connect (TAC)](https://github.com/twilio-innovation/twilio-agent-connect-python), enabling seamless integration with AWS Strands SDK.

## Features

- **StrandsConnector** - AWS Strands SDK integration with TAC
- Per-conversation agent isolation
- Multi-channel support (SMS + Voice)
- Automatic memory injection
- Context-aware agent factories

## Installation

### Basic Installation

```bash
pip install tac-aws
```

### With Strands SDK

```bash
# Install TAC AWS with Strands SDK
pip install tac-aws strands-agents

# For server support (adds FastAPI/Uvicorn via TAC)
pip install tac[server] tac-aws strands-agents
```

### Development

```bash
# Install with development tools (pytest, ruff, mypy)
pip install tac-aws[dev]
```


## Quick Start

### Example: Strands SDK with TAC Server

```python
from dotenv import load_dotenv
from strands import Agent
from tac import TAC, TACConfig
from tac.models.session import ConversationSession
from tac.server import TACFastAPIServer
from tac_aws.connectors import StrandsConnector

load_dotenv()

# Create TAC instance
tac = TAC(config=TACConfig.from_env())

# Agent factory receives conversation context (one agent per conversation)
def create_agent(context: ConversationSession) -> Agent:
    return Agent(
        model="amazon.nova-pro-v1:0",
        system_prompt=(
            "You are a helpful assistant. Remember everything the user tells you "
            "in this conversation and refer back to it when asked. Be concise and friendly."
        ),
    )

# Create connector (combines agent runtime + channel management)
connector = StrandsConnector(tac=tac, agent_factory=create_agent)

# TAC Server uses connector's channels for HTTP routing
server = TACFastAPIServer(tac=tac, voice_channel=connector.voice, sms_channel=connector.sms)
server.start()
```

## Configuration

TAC AWS requires TAC environment variables. See [TAC Configuration](https://github.com/twilio-innovation/twilio-agent-connect-python#configuration) for details.

### Required Environment Variables

```bash
# Twilio Configuration
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_API_KEY=your_api_key          # Starts with SK
TWILIO_API_TOKEN=your_api_token      # Secret for API key
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_CONVERSATION_SERVICE_SID=conv_configuration_xxx

# Server Configuration (for Voice)
TWILIO_TAC_VOICE_PUBLIC_DOMAIN=your-domain.ngrok.io
```

## Examples

Full example available in [`getting_started/examples/`](getting_started/examples/):

- `strands_agents.py` - Strands SDK with StrandsConnector and TAC Server

The example demonstrates the connector pattern with per-conversation agent isolation and automatic resource management.

## Deployment

See [`deploy/strands_aws_fargate/README.md`](deploy/strands_aws_fargate/README.md) for AWS Fargate deployment guide.

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/twilio-innovation/aws-twilio-agent-connect-python.git
cd aws-twilio-agent-connect-python

# Install dependencies
make sync

# Setup dev environment
make dev-setup
```

### Code Quality

```bash
# Format code
make format

# Type check
make type-check

# Lint
make lint

# Run tests
make test

# Run all checks
make check
```

## Dependencies

TAC AWS depends on:
- **tac** - Core Twilio Agent Connect framework (installed from GitHub)
  - Requires `tac[server]` extra for TAC Server support
- **strands-agents** (optional) - AWS Strands SDK

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Related Projects

- [Twilio Agent Connect (TAC)](https://github.com/twilio-innovation/twilio-agent-connect-python) - Core TAC framework
- [AWS Strands SDK](https://strandsagents.com/) - Multi-provider agent framework

## Support

For issues and questions:
- TAC AWS Issues: [GitHub Issues](https://github.com/twilio-innovation/aws-twilio-agent-connect-python/issues)
- TAC Core Issues: [TAC GitHub Issues](https://github.com/twilio-innovation/twilio-agent-connect-python/issues)
- Twilio Support: [Twilio Help Center](https://support.twilio.com/)
