<div align="center">
  <div>
    <img src="logo.svg" alt="Twilio Agent Connect AWS Logo" width="120" height="120">
  </div>

  <h1>
    Twilio Agent Connect AWS
  </h1>

  <h2>
    AWS integrations for Twilio Agent Connect — connect AWS agent services to Twilio's communication channels.
  </h2>

  <div align="center">
    <a href="https://pypi.org/project/twilio-agent-connect-aws/"><img alt="PyPI" src="https://img.shields.io/pypi/v/twilio-agent-connect-aws.svg"/></a>
    <a href="https://github.com/twilio/twilio-agent-connect-aws"><img alt="Python SDK" src="https://img.shields.io/badge/Python-3.10+-3776AB.svg"/></a>
    <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-green.svg"/></a>
    <a href="https://github.com/twilio/twilio-agent-connect-aws/actions/workflows/ci.yml"><img alt="CI Status" src="https://github.com/twilio/twilio-agent-connect-aws/actions/workflows/ci.yml/badge.svg"/></a>
    <a href="getting_started/examples/"><img alt="Getting Started" src="https://img.shields.io/badge/Getting%20Started-Examples-F22F46.svg"/></a>
  </div>
  
  <p>
    <a href="https://www.twilio.com/docs/platform/tac/overview">Documentation</a>
    ◆ <a href="https://github.com/twilio/twilio-agent-connect-python">Python SDK</a>
    ◆ <a href="getting_started/examples/">Examples</a>
    ◆ <a href="deploy/">Deployment</a>
  </p>
</div>

AWS-specific connectors for [Twilio Agent Connect (TAC)](https://github.com/twilio/twilio-agent-connect-python), enabling seamless integration with AWS agent services like Strands, Bedrock Agents, and Bedrock AgentCore.

---

## Features

### Agent Runtime Integration
- **AWS Strands SDK** - Build conversational agents with persistent session management and context-aware configuration
- **AWS Bedrock Agents** - Connect console-created agents with managed action groups and knowledge bases
- **AWS Bedrock AgentCore** - Deploy custom agent code (any framework: Strands, LangGraph, OpenAI SDK) with managed runtime
  - **Lambda Deployment** ⭐ **Recommended** - Serverless deployment with Lambda Function URL webhook proxy (no container infrastructure)
  - **Fargate Deployment** - Container-based deployment with `BedrockAgentCoreConnector` and FastAPI server on AWS Fargate

### Multi-Channel Communication
- **Voice and SMS support** - Single codebase handles both phone calls and text messages
- **Automatic conversation routing** - Messages route to the correct agent instance per conversation
- **Memory injection** - Customer history and preferences automatically included in agent context

### Deployment Options
- **FastAPI server** - Production-ready server with AWS ALB optimization and ngrok support for local testing (Fargate deployments)
- **Lambda Function URL proxy** - Serverless webhook handler with Twilio signature validation for AgentCore deployments
- **AgentCore runtime integration** - Server adapter for Bedrock AgentCore with HTTP (SMS) and WebSocket (voice) support

### Production Ready
- **Twilio webhook validation** - Automatic signature verification for secure integrations
- **Session persistence** - Continue conversations across interactions with built-in session management
- **Error handling** - Robust error handling and fallbacks for production reliability

## Installation

### With Strands SDK

```bash
pip install twilio-agent-connect-aws[strands,server]
```

### With Bedrock Agents

```bash
pip install twilio-agent-connect-aws[bedrock,server]
```

### With Bedrock AgentCore

```bash
pip install twilio-agent-connect-aws[agentcore,server]
```

### Development

```bash
# Install with development tools (includes all connectors)
pip install twilio-agent-connect-aws[dev]
```

## Configuration

twilio-agent-connect-aws requires TAC environment variables. See [TAC Configuration](https://github.com/twilio/twilio-agent-connect-python#configuration) for details.

### Required Environment Variables

```bash
# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_API_KEY=your_api_key          # Starts with SK
TWILIO_API_SECRET=your_api_secret    # Secret for API key
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_CONVERSATION_CONFIGURATION_ID=conv_configuration_xxx

# Server Configuration (for Voice)
TWILIO_VOICE_PUBLIC_DOMAIN=your-domain.ngrok.io
```

## Examples

Full examples available in [`getting_started/examples/`](getting_started/examples/):

- **`strands_agents.py`** - Strands SDK with per-conversation agent management
- **`bedrock_agents.py`** - AWS Bedrock Agents (console-created agents)
- **`bedrock_agentcore_agents.py`** - AWS Bedrock AgentCore (custom agent code deployment)

## Deployment

See [`deploy/README.md`](deploy/README.md) for production deployment guides:

### Container-based (Fargate)
- **Strands on Fargate** - Deploy Strands SDK agents with FastAPI server
- **Bedrock Agents on Fargate** - Deploy console-created Bedrock agents
- **AgentCore Connector on Fargate** - Deploy custom agent code with `BedrockAgentCoreConnector` and FastAPI server
  - Full control over server configuration
  - Use TAC connectors for multi-channel management

### Serverless (Lambda) ⭐ Recommended for AgentCore
- **AgentCore with Lambda** - Deploy AgentCore runtime with Lambda Function URL webhook proxy
  - No container infrastructure required
  - Automatic scaling with Lambda and AgentCore
  - Simpler deployment and lower operational overhead
  - Uses `AgentCoreLambdaProxy` and `TACAgentCoreApp` utilities
  - See [`deploy/agentcore_aws_lambda/`](deploy/agentcore_aws_lambda/) for setup guide

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/twilio/twilio-agent-connect-aws.git
cd twilio-agent-connect-aws

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

twilio-agent-connect-aws depends on:
- **tac** - Core Twilio Agent Connect framework (installed from GitHub)
  - Requires `tac[server]` extra for TAC Server support
- **strands-agents** (optional) - AWS Strands SDK

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see [LICENSE](LICENSE) file for details.

