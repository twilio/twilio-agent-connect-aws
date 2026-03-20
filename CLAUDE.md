# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TAC AWS is an open-source library providing AWS-specific integrations for Twilio Agent Connect (TAC). It contains adapters for AWS agent runtimes (Strands, Bedrock Agent Runtime, Bedrock AgentCore) and a FastAPI-based multi-channel server.

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
├── adapters/           # AWS adapter implementations
│   ├── __init__.py
│   ├── strands_adapter.py       # Strands SDK
│   ├── bedrock_adapter.py       # Bedrock Agent Runtime
│   └── agentcore_adapter.py     # Bedrock AgentCore
├── handlers/           # Multi-channel conversation management
│   ├── __init__.py
│   └── omni.py                  # OmniChannelHandlers (conversation logic)
└── servers/            # FastAPI-based servers
    ├── __init__.py
    └── fastapi.py               # OmniChannelFastAPIServer (HTTP routing)

getting_started/
└── examples/
    └── fastapi/        # FastAPI server examples
        ├── strands_agents.py
        ├── bedrock.py
        └── bedrock_agentcore.py
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
- `boto3` - AWS Bedrock (Agent Runtime and AgentCore)
- `server` - FastAPI + Uvicorn for OmniChannelFastAPIServer
- `dev` - Development tools (pytest, ruff, mypy, type stubs)

## Key Concepts

### Adapters

All adapters implement `BaseAgentAdapter` from TAC:

```python
from tac.adapters import BaseAgentAdapter

class MyAdapter(BaseAgentAdapter):
    async def run_async(self, message: str, session_id: str, **kwargs) -> str:
        # Call agent SDK
        pass

    async def stream_async(self, message: str, session_id: str, **kwargs):
        # Stream from agent SDK
        yield "chunk"
```

**Available Adapters:**
- `StrandsAdapter` - Wraps `strands.Agent`
- `BedrockAdapter` - Wraps boto3 `bedrock-agent-runtime` client
- `BedrockAgentCoreAdapter` - Wraps boto3 `bedrock-agentcore` client

### Handlers

**OmniChannelHandlers:**
- Manages conversation history per session
- Injects TAC memory context using `MemoryPromptBuilder`
- Invokes agent adapter with conversation history
- Routes responses to appropriate channel (Voice/SMS)
- Accepts `tac: TAC`, `adapter: BaseAgentAdapter`, and optional `voice` and `sms` channels
- Registers itself with TAC via `on_message_ready()` callback

### Server

**OmniChannelFastAPIServer:**
- Standalone FastAPI server (no base class)
- Accepts `handlers: OmniChannelHandlers` parameter for conversation management
- Optional `server_config: TACServerConfig` for server customization
- Creates FastAPI app with TAC routes (SMS, Voice, WebSocket, CI webhooks)
- HTTP routing layer - conversation logic handled by OmniChannelHandlers
- Clean separation: handlers manage conversation, server handles HTTP

## Import Patterns

### Correct Imports (from external TAC dependency)

```python
# TAC imports - external dependency
from tac.adapters import BaseAgentAdapter
from tac.core import TAC, TACConfig
from tac.models.session import ConversationSession
from tac.models.tac import TACMemoryResponse
from tac.server import TACServerConfig, FastAPIWebSocketAdapter

# TAC AWS imports - local package
from tac_aws.adapters import StrandsAdapter, BedrockAdapter
from tac_aws.servers import OmniChannelFastAPIServer
```

### Incorrect Imports (DO NOT DO)

```python
# ❌ Wrong - trying to import from tac_aws.core (doesn't exist)
from tac_aws.core import TAC

# ❌ Wrong - trying to import from tac source path
from src.tac.adapters import BaseAgentAdapter
```

## Type Hints for AWS Clients

**Bedrock Agent Runtime:**
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypy_boto3_bedrock_agent_runtime.client import AgentsforBedrockRuntimeClient

def __init__(self, client: AgentsforBedrockRuntimeClient, ...):
    self.client: AgentsforBedrockRuntimeClient = client
```

**Bedrock AgentCore:**
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypy_boto3_bedrock_agentcore.client import BedrockAgentCoreClient

def __init__(self, client: BedrockAgentCoreClient, ...):
    self.client: BedrockAgentCoreClient = client
```

## Example Usage Patterns

### Strands with FastAPI Server

```python
from strands import Agent
from tac import TAC, TACConfig
from tac.channels import SMSChannel, VoiceChannel
from tac_aws.adapters import StrandsAdapter
from tac_aws.handlers import OmniChannelHandlers
from tac_aws.servers import OmniChannelFastAPIServer

# Create TAC instance
tac = TAC(config=TACConfig.from_env())

# Create agent and adapter
agent = Agent(model="gpt-4o", system_prompt="You are helpful.")
adapter = StrandsAdapter(agent)

# Create channel handlers (manages conversation logic)
handlers = OmniChannelHandlers(
    tac=tac,
    adapter=adapter,
    voice=VoiceChannel(tac=tac, auto_retrieve_memory=True),
    sms=SMSChannel(tac=tac, auto_retrieve_memory=True),
)

# Create and start server (handles HTTP routing)
server = OmniChannelFastAPIServer(handlers=handlers)
server.start()
```

## Testing

Tests should:
- Import from `tac_aws` package (local)
- Import from `tac` package (external dependency)
- Use pytest fixtures for mocking AWS clients
- Test adapter implementations
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
3. **Don't forget TYPE_CHECKING guards** - for boto3 type hints
4. **Remember both servers use adapter pattern** - no @app.entrypoint decorator

## Related Documentation

- TAC Core: [CLAUDE.md](https://github.com/twilio-innovation/twilio-agent-connect-python/blob/main/CLAUDE.md)
- AWS Strands: [strandsagents.com/docs](https://strandsagents.com/docs)
- AWS Bedrock: [docs.aws.amazon.com/bedrock](https://docs.aws.amazon.com/bedrock/)
