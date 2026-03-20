# TAC AWS - AWS Integrations for Twilio Agent Connect

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AWS-specific adapters and servers for [Twilio Agent Connect (TAC)](https://github.com/twilio-innovation/twilio-agent-connect-python), enabling seamless integration with AWS agent runtimes including Strands SDK, Bedrock Agent Runtime, and Bedrock AgentCore.

## Features

✨ **Adapters for AWS Agent Runtimes:**
- **StrandsAdapter** - AWS Strands SDK integration with multi-provider support (OpenAI, Anthropic, Bedrock)
- **BedrockAdapter** - AWS Bedrock Agent Runtime integration
- **BedrockAgentCoreAdapter** - AWS Bedrock AgentCore service integration

🚀 **Multi-Channel Server:**
- **OmniChannelFastAPIServer** - FastAPI-based server for SMS and Voice channels with TAC integration

🎯 **Built on TAC:**
- Automatic memory retrieval and injection
- Profile management with trait groups
- Conversation history per session
- Framework-agnostic WebSocket protocol for Voice

## Installation

### Basic Installation

```bash
pip install tac-aws
```

### AWS SDK Dependencies

TAC AWS requires you to install AWS SDKs based on which features you need:

```bash
# For Strands SDK
pip install tac-aws strands-agents

# For AWS Bedrock Agent Runtime
pip install tac-aws boto3

# For AWS Bedrock AgentCore
pip install tac-aws bedrock-agentcore
```

### Server Support

```bash
# FastAPI-based OmniChannelFastAPIServer
pip install tac-aws[server] strands-agents

# For development (includes all dependencies)
pip install tac-aws[dev]  # Includes strands-agents, boto3, server
```

**Why separate?** This keeps the package lightweight and lets you choose exactly which AWS SDKs to install.


## Quick Start

### Example: Strands SDK with FastAPI Server

```python
from dotenv import load_dotenv
from strands import Agent
from tac import TAC, TACConfig
from tac.channels import SMSChannel, VoiceChannel
from tac_aws.adapters import StrandsAdapter
from tac_aws.handlers import OmniChannelHandlers
from tac_aws.servers import OmniChannelFastAPIServer

load_dotenv()

# Create TAC instance
tac = TAC(config=TACConfig.from_env())

# Create Strands agent
agent = Agent(
    model="gpt-4o",
    system_prompt="You are a helpful customer service agent."
)

# Wrap in adapter
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

### Example: Bedrock Agent Runtime

```python
import boto3
from tac import TAC, TACConfig
from tac.channels import SMSChannel, VoiceChannel
from tac_aws.adapters import BedrockAdapter
from tac_aws.handlers import OmniChannelHandlers
from tac_aws.servers import OmniChannelFastAPIServer

# Create TAC instance
tac = TAC(config=TACConfig.from_env())

# Create Bedrock client
bedrock_client = boto3.client("bedrock-agent-runtime", region_name="us-east-1")

# Create adapter
adapter = BedrockAdapter(
    client=bedrock_client,
    agent_id="your-agent-id",
    agent_alias_id="your-alias-id",
    enable_trace=True
)

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

## Architecture

TAC AWS follows the adapter pattern for clean integration with different agent runtimes:

```
Agent SDK/Service → Adapter → OmniChannel Server → TAC Channels (SMS/Voice)
```

### Adapters

All adapters implement the `BaseAgentAdapter` interface from TAC:

```python
from tac.adapters import BaseAgentAdapter

class MyAdapter(BaseAgentAdapter):
    async def run_async(self, message: str, session_id: str, **kwargs) -> str:
        # Your implementation
        pass

    async def stream_async(self, message: str, session_id: str, **kwargs):
        # Your streaming implementation
        yield "chunk"
```

### Server

**OmniChannelFastAPIServer:**
- FastAPI-based with TAC integration
- Adapter pattern for any agent runtime
- Multi-channel support (SMS + Voice)
- Memory retrieval and injection
- Per-conversation history management
- Automatic response routing
- WebSocket support for Voice
- Conversation Intelligence webhook support

## Configuration

TAC AWS requires TAC environment variables. See [TAC Configuration](https://github.com/twilio-innovation/twilio-agent-connect-python#configuration) for details.

### Required Environment Variables

```bash
# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid
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

Full examples are available in [`getting_started/examples/fastapi/`](getting_started/examples/fastapi/):

- `strands_agents.py` - Strands SDK with OmniChannelFastAPIServer
- `bedrock.py` - Bedrock Agent Runtime with OmniChannelFastAPIServer
- `bedrock_agentcore.py` - Bedrock AgentCore with OmniChannelFastAPIServer

All examples use the same adapter pattern and FastAPI server.

See [`getting_started/examples/README.md`](getting_started/examples/README.md) for detailed documentation.

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
- **strands-agents** (optional) - AWS Strands SDK
- **boto3** (optional) - AWS SDK for Bedrock services (Agent Runtime and AgentCore)
- **fastapi** + **uvicorn** (optional) - For OmniChannelFastAPIServer (`[server]` extra)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Related Projects

- [Twilio Agent Connect (TAC)](https://github.com/twilio-innovation/twilio-agent-connect-python) - Core TAC framework
- [AWS Strands SDK](https://strandsagents.com/) - Multi-provider agent framework
- [AWS Bedrock](https://aws.amazon.com/bedrock/) - Foundation models and agent services

## Support

For issues and questions:
- TAC AWS Issues: [GitHub Issues](https://github.com/twilio-innovation/aws-twilio-agent-connect-python/issues)
- TAC Core Issues: [TAC GitHub Issues](https://github.com/twilio-innovation/twilio-agent-connect-python/issues)
- Twilio Support: [Twilio Help Center](https://support.twilio.com/)
