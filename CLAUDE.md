# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TAC AWS is an open-source library providing AWS-specific integrations for Twilio Agent Connect (TAC). It contains connectors that combine agent runtime integration with multi-channel conversation management.

**Key Architecture**: TAC AWS is a separate package that depends on TAC as an external dependency. It does NOT contain TAC source code - it imports from the `tac` package.

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
├── connectors/         # AWS agent connectors (combines runtime + channels)
│   ├── __init__.py
│   └── strands_connector.py     # StrandsConnector (Strands SDK integration)
└── tools/              # LLM tools for Strands
    └── strands.py               # Memory tool for Strands agents

getting_started/
└── examples/           # FastAPI server examples
    └── strands_agents.py

deploy/
└── strands_aws_fargate/    # AWS Fargate deployment
    ├── Dockerfile          # Multi-stage Docker build
    ├── cloudformation.yaml # ECS Fargate + ALB infrastructure
    ├── README.md           # Deployment guide
    ├── build-wheels.sh     # Build wheels for private dependencies
    ├── requirements.txt    # Production dependencies
    └── strands_server.py   # Production server entry point
```

## Code Conventions

- **Python 3.10+**: Use `typing` module types (`List`, `Dict`, `Optional`)
- **mypy strict**: All functions need type hints, no incomplete defs
- **ruff**: Line length 100, black-compatible formatting
- **Imports from TAC**: Always import from `tac` package, never from internal `tac_aws` except for local imports

## Dependencies

### Core Dependency

TAC AWS depends on TAC from GitHub (locked to specific commit):

```toml
dependencies = [
    "tac @ git+https://github.com/twilio-innovation/twilio-agent-connect-python.git@{commit_hash}",
]
```

### Optional Dependencies

- `strands-agents` - AWS Strands SDK
- `dev` - Development tools (pytest, ruff, mypy, type stubs)

**Note**: Server support requires `tac[server]` from the core TAC package.

## Key Concepts

### Connectors

Connectors combine agent runtime integration with multi-channel conversation management. They provide a unified interface that:
- Creates and manages per-conversation agent instances
- Creates Voice and SMS channels
- Injects TAC memory context using `MemoryPromptBuilder`
- Routes responses to appropriate channels
- Registers with TAC via `on_message_ready()` callback

**Available Connectors:**

**StrandsConnector:**
- AWS Strands SDK integration with per-conversation agent management
- Accepts `tac: TAC`, `agent_factory: Callable[[ConversationSession], Agent]`, and optional channel configs
- Agent factory receives `ConversationSession` context with conversation_id, channel, customer_id, etc.
- Enables SessionManager usage and context-aware agent configuration
- Provides `voice` and `sms` channel instances for server integration
- Handles conversation history through Strands' built-in message management

### Server

TAC AWS uses `TACFastAPIServer` from the core TAC package (`tac.server`):
- FastAPI-based server with TAC integration
- Accepts voice and SMS channel instances from connector
- Handles HTTP routes (SMS, Voice, WebSocket, CI webhooks)
- Clean separation: connector manages conversation, TACFastAPIServer handles HTTP

## Import Patterns

### Correct Imports (from external TAC dependency)

```python
# TAC imports - external dependency
from tac.core import TAC, TACConfig
from tac.models.session import ConversationSession
from tac.models.tac import TACMemoryResponse
from tac.server import TACFastAPIServer

# TAC AWS imports - local package
from tac_aws.connectors import StrandsConnector
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

# Create TAC instance
tac = TAC(config=TACConfig.from_env())

# Agent factory receives conversation context
def create_agent(context: ConversationSession) -> Agent:
    return Agent(
        model="amazon.nova-pro-v1:0",
        system_prompt="You are a helpful assistant."
    )

# Create connector (combines agent runtime + channel management)
connector = StrandsConnector(tac=tac, agent_factory=create_agent)

# TAC Server uses connector's channels for HTTP routing
server = TACFastAPIServer(tac=tac, voice_channel=connector.voice, sms_channel=connector.sms)
server.start()
```

### Using SessionManager for Persistence

```python
from strands import Agent
from strands.session.file import FileSessionManager
from tac.models.session import ConversationSession

def create_agent(context: ConversationSession) -> Agent:
    """Agent factory with SessionManager for conversation persistence."""
    return Agent(
        model="amazon.nova-pro-v1:0",
        system_prompt="You are a helpful assistant.",
        session_manager=FileSessionManager(
            session_id=context.conversation_id,
            base_path="./sessions"
        )
    )

connector = StrandsConnector(tac=tac, agent_factory=create_agent)
```

### Context-Aware Agent Configuration

```python
def create_agent(context: ConversationSession) -> Agent:
    """Customize agent behavior based on conversation context."""
    # Different prompts for different channels
    if context.channel == "voice":
        prompt = "You are a helpful voice assistant. Keep responses concise."
    else:  # SMS
        prompt = "You are a helpful SMS assistant. Use short messages."

    return Agent(
        model="amazon.nova-pro-v1:0",
        system_prompt=prompt,
        agent_id=context.conversation_id,
        name=f"Agent-{context.channel}"
    )
```

## Testing

Tests should:
- Import from `tac_aws` package (local)
- Import from `tac` package (external dependency)
- Use pytest fixtures for mocking AWS clients
- Test connector implementations
- Test server initialization and routing

## Updating TAC Dependency

When TAC has new changes, update the commit hash in pyproject.toml:

```bash
# In TAC repo
git rev-parse HEAD

# In TAC AWS repo
# Update pyproject.toml with new commit hash
sed -i '' 's/@{old_hash}/@{new_hash}/g' pyproject.toml
```

## Common Pitfalls

1. **Don't import from internal tac_aws paths for TAC classes** - use `from tac.X import Y`
2. **Don't copy TAC source code** - TAC is a dependency, not vendored
3. **Don't forget TYPE_CHECKING guards** - for boto3 and strands type hints
4. **Connectors manage both agent runtime and channels** - don't create separate channel instances

## Related Documentation

- TAC Core: [CLAUDE.md](https://github.com/twilio-innovation/twilio-agent-connect-python/blob/main/CLAUDE.md)
- AWS Strands: [strandsagents.com/docs](https://strandsagents.com/docs)
- AWS Bedrock: [docs.aws.amazon.com/bedrock](https://docs.aws.amazon.com/bedrock/)
