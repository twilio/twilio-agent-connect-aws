# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

twilio-agent-connect-aws is an open-source library providing AWS-specific integrations for Twilio Agent Connect (TAC). It contains connectors that combine agent runtime integration with multi-channel conversation management.

**Key Architecture**: twilio-agent-connect-aws is a separate package that depends on TAC as an external dependency. It does NOT contain TAC source code - it imports from the `tac` package.

## Understanding TAC

TAC (Twilio Agent Connect) is middleware that integrates with Twilio platform services:
- **Conversation Orchestrator** - Organizes voice/SMS/WhatsApp into conversations
- **Conversation Memory** - Stores customer context, preferences, and history
- **Conversation Intelligence** - Extracts insights via language operators
- **Knowledge** - Semantic search over knowledge bases

**In twilio-agent-connect-aws**: Connectors use TAC to inject memory context into agent prompts and route messages to the appropriate agent instance per conversation.

## Development Commands

```bash
make sync              # Install dependencies (uses uv)
make dev-setup         # Full dev setup with pre-commit hooks
make format            # Format with ruff
make lint              # Lint check only
make type-check        # mypy strict mode
make test              # Run pytest
make check             # All checks (lint + type-check + test)
```

## Package Structure

```
src/tac_aws/
├── __init__.py         # Package exports
├── connectors/         # AWS agent connectors (runtime + channels)
│   ├── strands_connector.py               # StrandsConnector
│   ├── bedrock_connector.py               # BedrockConnector
│   └── bedrock_agentcore_connector.py     # BedrockAgentCoreConnector
├── proxy/              # Lambda proxy handlers (requires agentcore extra)
│   ├── agentcore_lambda.py                # AgentCoreLambdaProxy
│   └── validation.py                      # TwilioSignatureValidator
├── server/             # Server utilities (requires server extra)
│   ├── fastapi_server.py                  # TACAWSFastAPIServer
│   └── agentcore_app.py                   # TACAgentCoreApp (requires agentcore extra)
└── tools/              # LLM tools for Strands
    └── strands.py                         # Memory tool for Strands agents

getting_started/examples/   # Full working examples (FastAPI servers)
deploy/                     # Production deployment guides
```

## Code Conventions

- **Python 3.10+**: Use `typing` module types (`List`, `Dict`, `Optional`)
- **mypy strict**: All functions need type hints, no incomplete defs
- **ruff**: Line length 100, black-compatible formatting
- **Imports from TAC**: Always import from `tac` package, never from internal `tac_aws` except for local imports

## Dependencies

### Core Dependency

```toml
dependencies = [
    "twilio-agent-connect>=1.0.0,<2",
]
```

### Optional Dependencies

- `strands` - AWS Strands SDK
- `bedrock` - AWS Bedrock Agents (boto3 + type stubs)
- `agentcore` - AWS Bedrock AgentCore (bedrock-agentcore + boto3 + type stubs)
- `server` - FastAPI server utilities (requires `tac[server]`)
- `dev` - Development tools (pytest, ruff, mypy, type stubs)

## Key Concepts

### Connectors

Connectors combine agent runtime integration with multi-channel conversation management:
- Create and manage per-conversation agent instances
- Create Voice and SMS channels
- Inject TAC memory context using `MemoryPromptBuilder`
- Route responses to appropriate channels
- Register with TAC via `on_message_ready()` callback

**StrandsConnector**: AWS Strands SDK integration with per-conversation agent management and SessionManager support.

**BedrockConnector**: AWS Bedrock Agents integration for console-created agents with managed service.

**BedrockAgentCoreConnector**: AWS Bedrock AgentCore integration for custom agent code (Strands, LangGraph, OpenAI SDK). Supports both HTTP and WebSocket runtimes.

### Server Utilities

**TACAWSFastAPIServer**: FastAPI server with AWS ALB header fixing for Twilio signature validation.

**TACAgentCoreApp**: TAC adapter for AgentCore runtime. Registers HTTP (SMS) and WebSocket (Voice) handlers.

**TACAgentCoreWebSocketAdapter**: WebSocket wrapper that sends welcome greeting for Twilio ConversationRelay.

### Proxy Utilities (Lambda)

**AgentCoreLambdaProxy**: Routes Twilio webhooks to AgentCore runtime. Handles signature validation, voice TwiML generation, and webhook forwarding.

**TwilioSignatureValidator**: Webhook signature validation for Lambda events (form-encoded and JSON).

## Import Patterns

### Correct Imports

```python
# TAC imports - external dependency
from tac.core import TAC, TACConfig
from tac.models.session import ConversationSession
from tac.server import TACFastAPIServer

# twilio-agent-connect-aws imports - local package
from tac_aws.connectors import StrandsConnector, BedrockAgentCoreConnector
from tac_aws.proxy import AgentCoreLambdaProxy, TwilioSignatureValidator
from tac_aws.server import TACAgentCoreApp, TACAWSFastAPIServer
```

### Incorrect Imports (DO NOT DO)

```python
# ❌ Wrong - trying to import from tac_aws.core (doesn't exist)
from tac_aws.core import TAC

# ❌ Wrong - trying to import from tac source path
from src.tac.adapters import BaseAgentAdapter
```

## Example Usage Patterns

### Strands with TAC Server

```python
from strands import Agent
from tac import TAC, TACConfig
from tac.models.session import ConversationSession
from tac.server import TACFastAPIServer
from tac_aws.connectors import StrandsConnector

tac = TAC(config=TACConfig.from_env())

def create_agent(context: ConversationSession) -> Agent:
    """Agent factory receives conversation context."""
    return Agent(
        model="amazon.nova-pro-v1:0",
        system_prompt="You are a helpful assistant."
    )

connector = StrandsConnector(tac=tac, agent_factory=create_agent)
server = TACFastAPIServer(tac=tac, voice_channel=connector.voice, messaging_channels=[connector.sms])
server.start()
```

**See full examples**: `getting_started/examples/strands_agents.py`

### AgentCore Lambda Proxy

```python
import json
import os
import boto3
from tac_aws.proxy import AgentCoreLambdaProxy

# Fetch Twilio auth token from Secrets Manager
secrets_client = boto3.client("secretsmanager", region_name=os.environ["AWS_REGION"])
response = secrets_client.get_secret_value(SecretId=os.environ["TWILIO_SECRET_ARN"])
credentials = json.loads(response["SecretString"])

proxy = AgentCoreLambdaProxy(
    agentcore_runtime_arn=os.environ["AGENTCORE_RUNTIME_ARN"],
    conversation_configuration_id=os.environ["TWILIO_CONVERSATION_CONFIGURATION_ID"],
    twilio_auth_token=credentials["TWILIO_AUTH_TOKEN"],
)

lambda_handler = proxy.lambda_handler
```

**See full examples**: `deploy/agentcore_aws_lambda/lambda/index.py`

### AgentCore Server App

```python
from tac import TAC, TACConfig
from tac_aws.connectors import StrandsConnector
from tac_aws.server import TACAgentCoreApp

tac = TAC(config=TACConfig.from_env())
connector = StrandsConnector(tac=tac, agent_factory=create_agent)

tac_app = TACAgentCoreApp(
    tac=tac,
    voice_channel=connector.voice,
    sms_channel=connector.sms,
)

app = tac_app.app  # Expose for AgentCore runtime
```

**See full examples**: `deploy/agentcore_aws_lambda/agent/main.py`

### Bedrock Agents

```python
import boto3
from tac_aws.connectors import BedrockConnector

client = boto3.client("bedrock-agent-runtime", region_name="us-east-1")

# Simple config - sessionId and inputText auto-injected
connector = BedrockConnector(
    tac=tac,
    bedrock_client=client,
    config={"agentId": "AGENT123", "agentAliasId": "TSTALIASID"},
)
```

**See full examples**: `getting_started/examples/bedrock_agents.py`

### Bedrock AgentCore

```python
from tac_aws.connectors import BedrockAgentCoreConnector
from tac_aws.connectors.bedrock_agentcore.config import RuntimeConfig, WebSocketConfig

# Dual-runtime: HTTP (required) + WebSocket (optional for low-latency voice)
connector = BedrockAgentCoreConnector(
    tac=tac,
    runtime=RuntimeConfig(
        http=invoke_agent_http,  # Required for both channels
        websocket=WebSocketConfig(  # Optional voice optimization
            factory=create_websocket,
            payload_fn=build_websocket_payload,
        ),
    ),
)
```

**See full examples**: `getting_started/examples/bedrock_agentcore_agents.py`

## Testing

Tests should:
- Import from `tac_aws` package (local)
- Import from `tac` package (external dependency)
- Use pytest fixtures for mocking AWS clients
- Test connector implementations
- Test server initialization and routing

## Common Pitfalls

1. **Don't import from internal tac_aws paths for TAC classes** - use `from tac.X import Y`
2. **Don't copy TAC source code** - TAC is a dependency, not vendored
3. **Don't forget TYPE_CHECKING guards** - for boto3 and strands type hints
4. **Connectors manage both agent runtime and channels** - don't create separate channel instances
5. **Optional dependencies are gated** - proxy requires `agentcore`, server requires `tac[server]`

## Related Documentation

- TAC Core: [twilio-agent-connect-python](https://github.com/twilio/twilio-agent-connect-python)
- AWS Strands: [strandsagents.com/docs](https://strandsagents.com/docs)
- AWS Bedrock: [docs.aws.amazon.com/bedrock](https://docs.aws.amazon.com/bedrock/)
- Examples: `getting_started/examples/`
- Deployment: `deploy/README.md`
