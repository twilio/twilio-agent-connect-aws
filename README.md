# TAC AWS - AWS Integrations for Twilio Agent Connect

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AWS-specific adapters and handlers for [Twilio Agent Connect (TAC)](https://github.com/twilio-innovation/twilio-agent-connect-python), enabling seamless integration with AWS Strands SDK.

## Features

✨ **AWS Strands SDK Adapter:**
- **StrandsAdapter** - AWS Strands SDK integration with per-conversation agent instances
- Multi-provider support (OpenAI, Anthropic, Bedrock models)
- Automatic conversation history management

🚀 **Multi-Channel Handler:**
- **OmniChannelHandler** - Manages conversation flow across SMS and Voice channels
- Works with TAC Server for HTTP/WebSocket handling
- Automatic memory injection and response routing

🎯 **Built on TAC:**
- Automatic memory retrieval and injection
- Profile management with trait groups
- Per-conversation history isolation
- Framework-agnostic WebSocket protocol for Voice

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
from tac.server import TACFastAPIServer
from tac_aws.adapters import StrandsAdapter
from tac_aws.handlers import OmniChannelHandler

load_dotenv()

# Create TAC instance
tac = TAC(config=TACConfig.from_env())

# Create agent factory (one agent per conversation)
def create_agent() -> Agent:
    return Agent(
        model="amazon.nova-pro-v1:0",
        system_prompt=(
            "You are a helpful assistant. Remember everything the user tells you "
            "in this conversation and refer back to it when asked. Be concise and friendly."
        ),
    )

# Create adapter with agent factory
adapter = StrandsAdapter(agent_factory=create_agent)

# Create channel handler
handler = OmniChannelHandler(tac=tac, adapter=adapter)

# TAC Server uses handler's channels for HTTP routing
server = TACFastAPIServer(tac=tac, voice_channel=handler.voice, sms_channel=handler.sms)
server.start()
```


## Architecture

TAC AWS follows the adapter pattern for clean integration with different agent runtimes:

```
Agent SDK/Service → Adapter → OmniChannelHandler → TAC Channels (SMS/Voice) → TAC Server
```

### Adapters

All adapters implement the `BaseAgentAdapter` interface:

```python
from tac_aws.adapters import BaseAgentAdapter

class MyAdapter(BaseAgentAdapter):
    async def run_async(self, message: str, conversation_id: str, **kwargs) -> str:
        # Your implementation
        pass

    async def stream_async(self, message: str, conversation_id: str, **kwargs):
        # Your streaming implementation
        yield "chunk"
```

### Handler

**OmniChannelHandler:**
- Manages conversation flow across channels
- Adapter pattern for any agent runtime
- Multi-channel support (SMS + Voice)
- Memory retrieval and injection
- Per-conversation history management
- Automatic response routing
- Works with TAC Server for HTTP/WebSocket handling

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

# TAC Environment (optional, defaults to prod)
TWILIO_TAC_ENVIRONMENT=prod          # or dev, stage

# Server Configuration (for Voice)
TWILIO_TAC_VOICE_PUBLIC_DOMAIN=your-domain.ngrok.io
```

### Optional Configuration

```bash
# Memory Configuration
TWILIO_TAC_MEMORY_TRAIT_GROUPS=Contact,Preferences

# Conversation Intelligence
TWILIO_TAC_CI_CONFIGURATION_ID=your_ci_config_id
TWILIO_TAC_CI_OBSERVATION_OPERATOR_SID=LY...
TWILIO_TAC_CI_SUMMARY_OPERATOR_SID=LY...
```

## Examples

Full example available in [`getting_started/examples/`](getting_started/examples/):

- `strands_agents.py` - Strands SDK with OmniChannelHandler and TAC Server

The example demonstrates the adapter pattern with conversation history management.

## Deployment

### AWS Fargate

Production-ready deployment with ECS Fargate and Application Load Balancer:

```bash
cd deploy/strands_aws_fargate

# Build wheels for private dependencies
./build-wheels.sh

# Build Docker image
docker build -t tac-strands-server:latest -f Dockerfile .

# Deploy to AWS (see deploy/strands_aws_fargate/README.md for full guide)
aws cloudformation deploy --template-file cloudformation.yaml --stack-name TACStack ...
```

See [`deploy/strands_aws_fargate/README.md`](deploy/strands_aws_fargate/README.md) for complete deployment guide with:
- CloudFormation infrastructure setup
- Docker multi-stage builds
- ALB configuration
- Architecture diagrams
- Production best practices

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
