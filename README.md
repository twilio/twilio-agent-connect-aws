# TAC AWS - AWS Integrations for Twilio Agent Connect

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AWS-specific connectors for [Twilio Agent Connect (TAC)](https://github.com/twilio-innovation/twilio-agent-connect-python), enabling seamless integration with AWS agent services.

## Features

- **StrandsConnector** - AWS Strands SDK integration
  - Per-conversation agent isolation with SessionManager support
  - Context-aware agent factories
- **BedrockConnector** - AWS Bedrock Agents integration
  - Connect console-created agents to Twilio
  - Managed agent service with action groups and knowledge bases
- **BedrockAgentCoreConnector** - AWS Bedrock AgentCore integration
  - Deploy custom agent code (Strands, LangGraph, OpenAI SDK)
  - Managed runtime with built-in memory
- Multi-channel support (SMS + Voice)
- Automatic TAC memory injection

## Installation

### With Strands SDK

```bash
pip install tac-aws[strands,server]
```

### With Bedrock Agents

```bash
pip install tac-aws[bedrock,server]
```

### With Bedrock AgentCore

```bash
pip install tac-aws[agentcore,server]
```

### Development

```bash
# Install with development tools (includes all connectors)
pip install tac-aws[dev]
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

Full examples available in [`getting_started/examples/`](getting_started/examples/):

- **`strands_agents.py`** - Strands SDK with per-conversation agent management
- **`bedrock_agents.py`** - AWS Bedrock Agents (console-created agents)
- **`bedrock_agentcore_agents.py`** - AWS Bedrock AgentCore (custom agent code deployment)

## Deployment

See [`deploy/README.md`](deploy/README.md) for production deployment guides.

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

