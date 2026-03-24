# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TAC AWS is an open-source library providing AWS-specific integrations for Twilio Agent Connect (TAC). It contains adapters for AWS Strands SDK and multi-channel conversation handlers.

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
│   ├── base.py                  # BaseAgentAdapter interface
│   └── strands_adapter.py       # Strands SDK
├── handlers/           # Multi-channel conversation management
│   ├── __init__.py
│   └── omni.py                  # OmniChannelHandler (conversation logic)
└── tools/              # LLM tools for Strands
    └── strands.py               # Memory tool for Strands agents

getting_started/
└── examples/           # FastAPI server examples
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
- `dev` - Development tools (pytest, ruff, mypy, type stubs)

**Note**: Server support requires `tac[server]` from the core TAC package.

## Key Concepts

### Adapters

All adapters implement `BaseAgentAdapter`:

```python
from tac_aws.adapters import BaseAgentAdapter

class MyAdapter(BaseAgentAdapter):
    async def run_async(self, message: str, conversation_id: str, **kwargs) -> str:
        # Call agent SDK
        pass

    async def stream_async(self, message: str, conversation_id: str, **kwargs):
        # Stream from agent SDK
        yield "chunk"
```

**Available Adapters:**
- `StrandsAdapter` - Wraps `strands.Agent` with per-conversation agent instances

### Handlers

**OmniChannelHandler:**
- Manages conversation history per session
- Injects TAC memory context using `MemoryPromptBuilder`
- Invokes agent adapter with conversation history
- Routes responses to appropriate channel (Voice/SMS)
- Accepts `tac: TAC`, `adapter: BaseAgentAdapter`, and optional `voice` and `sms` channels
- Registers itself with TAC via `on_message_ready()` callback

### Server

TAC AWS uses `TACFastAPIServer` from the core TAC package (`tac.server`):
- FastAPI-based server with TAC integration
- Accepts voice and SMS channel instances
- Handles HTTP routes (SMS, Voice, WebSocket, CI webhooks)
- OmniChannelHandler creates channels and manages conversation logic
- Clean separation: handler manages conversation, TACFastAPIServer handles HTTP

## Import Patterns

### Correct Imports (from external TAC dependency)

```python
# TAC imports - external dependency
from tac.core import TAC, TACConfig
from tac.models.session import ConversationSession
from tac.models.tac import TACMemoryResponse
from tac.server import TACFastAPIServer

# TAC AWS imports - local package
from tac_aws.adapters import BaseAgentAdapter, StrandsAdapter
from tac_aws.handlers import OmniChannelHandler
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
from tac.server import TACFastAPIServer
from tac_aws.adapters import StrandsAdapter
from tac_aws.handlers import OmniChannelHandler

# Create TAC instance
tac = TAC(config=TACConfig.from_env())

# Create agent factory and adapter
def create_agent() -> Agent:
    return Agent(
        model="amazon.nova-pro-v1:0",
        system_prompt="You are a helpful assistant."
    )

adapter = StrandsAdapter(agent_factory=create_agent)

# Create channel handler (manages conversation logic)
handler = OmniChannelHandler(tac=tac, adapter=adapter)

# TAC Server uses handler's channels for HTTP routing
server = TACFastAPIServer(tac=tac, voice_channel=handler.voice, sms_channel=handler.sms)
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
