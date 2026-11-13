# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Keep it accurate: when a change alters anything described here (behavior, commands, layout, CI), update this file in the same PR.

If a PR, including later pushes to it, conflicts with anything in this file, the PR must also update this file to match before it merges.

## Project Overview

twilio-agent-connect-aws is an open-source library providing AWS integrations for Twilio Agent Connect (TAC). It contains connectors that combine an AWS agent runtime integration with multi-channel conversation management.

**Key Architecture**: twilio-agent-connect-aws is a separate package that depends on TAC (core Python) as an external dependency. It does NOT contain TAC source code — it imports from the `tac` package.

## Understanding TAC

TAC (Twilio Agent Connect) is middleware that integrates with Twilio platform services:
- **Conversation Orchestrator** - Organizes voice/SMS/WhatsApp into conversations
- **Conversation Memory** - Stores customer context, preferences, and history
- **Conversation Intelligence** - Extracts insights via language operators
- **Knowledge** - Semantic search over knowledge bases

**In twilio-agent-connect-aws**: Connectors register `on_message_ready()` (and, where they hold per-conversation state, `on_conversation_ended()`) callbacks on a `TAC` instance, inject Conversation Memory into the agent prompt via `MemoryPromptBuilder`, and route each reply back on the channel it arrived on. The TAC conversation id is the key for per-conversation agent state (a Strands agent instance, a Bedrock or AgentCore session).

## Development Commands

```bash
make sync              # Install dependencies (uv sync --all-extras --all-packages)
make dev-setup         # Full dev setup (sync + pre-commit hooks)
make format            # Format with ruff
make lint              # Lint check only
make type-check        # mypy (disallow_untyped_defs)
make test              # Run pytest
make check             # All checks (lint + type-check + test)
make docs              # Build the docs site into site/ (--strict, fails on broken links)
make docs-serve        # Serve docs locally with live reload
make docs-versions     # List versioned docs published to gh-pages
```

Lint and format run ruff over the whole repo; mypy covers `src/tac_aws`, `getting_started` and `deploy`; pytest covers `tests/`.

## Package Structure

```
src/tac_aws/
├── __init__.py                          # Only exposes __version__ (see Import Patterns)
├── _version.py
├── connectors/                          # AWS agent connectors (runtime + channels)
│   ├── channels.py                      # ConnectorChannels (shared channel set + routing)
│   ├── strands_connector.py             # StrandsConnector
│   ├── bedrock_connector.py             # BedrockConnector
│   └── bedrock_agentcore/               # BedrockAgentCoreConnector (connector, config, http, websocket)
├── proxy/                               # Lambda proxy handlers (requires agentcore extra)
│   ├── agentcore_lambda.py              # AgentCoreLambdaProxy
│   └── validation.py                    # TwilioSignatureValidator
├── server/                              # Server utilities (requires server extra)
│   ├── fastapi_server.py                # TACAWSFastAPIServer
│   ├── middleware.py                    # ALB header fixing for signature validation
│   └── agentcore_app.py                 # TACAgentCoreApp (requires agentcore extra)
└── tools/
    └── strands/                         # Memory tool for Strands agents

tests/                                   # pytest suite, one module per connector/component
getting_started/examples/                # Runnable FastAPI examples per connector
deploy/                                  # Deployment guides (Fargate, AgentCore + Lambda)
docs/                                    # MkDocs sources for the published API reference
```

## Code Conventions

- **Python 3.10+**: `requires-python` is `>=3.10`. Use modern syntax (`str | None`, `list[str]`) with `from __future__ import annotations`.
- **mypy**: `disallow_untyped_defs` and `disallow_incomplete_defs` are on, so every function needs full type hints. Guard boto3 and Strands type-only imports with `TYPE_CHECKING`.
- **ruff**: Line length 100, rule sets `E W F I B C4 UP N`, isort ordering with `tac_aws` as first-party.
- **Imports from TAC**: Always import from the `tac` package; never copy or re-export TAC classes from `tac_aws`.

## Dependencies

### Core Dependency

```toml
dependencies = [
    "twilio-agent-connect>=2.3.0,<3",
]
```

### Optional Extras

Each runtime's AWS SDK is only required by its own extra, so installing with no extras never fails on import.

- `server` - FastAPI server utilities (`twilio-agent-connect[server]`)
- `strands` - AWS Strands SDK
- `bedrock` - AWS Bedrock Agents (boto3 + type stubs)
- `agentcore` - AWS Bedrock AgentCore (bedrock-agentcore + boto3 + type stubs)
- `dev` - All SDKs plus pytest, ruff, mypy and type stubs
- `docs` is a dependency group (`uv run --group docs ...`), not an extra

## Key Concepts

### Connectors

Connectors combine agent runtime integration with channel management. Each one:
- Builds the channel set via `ConnectorChannels`: Voice, SMS and Chat always; RCS and WhatsApp only when `TACConfig.rcs_sender_id` / `whatsapp_number` is configured. Their `*_config` args are tuning only and never enable a channel.
- Exposes channels as attributes (`voice`, `sms`, `chat`, and `rcs` / `whatsapp`, which are `None` when not configured).
- Registers with TAC via `on_message_ready()`; Strands and AgentCore also register `on_conversation_ended()` to drop per-conversation state.
- Injects Conversation Memory into the agent prompt via `MemoryPromptBuilder`.

**ConnectorChannels** (`connectors/channels.py`): shared by all three connectors. `channels.messaging` is the list to hand a server as `messaging_channels=`; `channels.send(context, response)` routes a reply back on the channel it arrived on, buffering a streamed response for messaging channels and passing it through token-by-token for voice.

**StrandsConnector**: AWS Strands SDK integration with per-conversation agent management and SessionManager support.

**BedrockConnector**: AWS Bedrock Agents integration for console-created agents with managed service.

**BedrockAgentCoreConnector**: AWS Bedrock AgentCore integration for custom agent code (Strands, LangGraph, OpenAI SDK). Supports both HTTP and WebSocket runtimes.

### Server

**TACAWSFastAPIServer**: FastAPI server with AWS ALB header fixing for Twilio signature validation. Reads the public domain from `TACConfig.voice_public_domain` (TAC 2.x moved it off `TACServerConfig`).

**TACAgentCoreApp**: TAC adapter for AgentCore runtime. Registers HTTP (SMS) and WebSocket (Voice) handlers.

**TACAgentCoreWebSocketAdapter**: WebSocket wrapper that sends welcome greeting for Twilio ConversationRelay.

### Proxy (Lambda)

**AgentCoreLambdaProxy**: Routes Twilio webhooks to AgentCore runtime. Handles signature validation, voice TwiML generation, and webhook forwarding. Exposes TAC's ConversationRelay TwiML customization for Lambda deployments (no `VoiceChannel` exists there): static `twiml_options=TwiMLOptions(...)` plus a per-call `on_inbound_call_twiml(...)` customizer, merged over the presigned `websocket_url` and `conversation_configuration` defaults.

**TwilioSignatureValidator**: Webhook signature validation for Lambda events (form-encoded and JSON).

## Import Patterns

### Correct Imports

```python
# TAC imports - external dependency
from tac import TAC, TACConfig
from tac.models.session import ConversationSession
from tac.server import TACFastAPIServer

# twilio-agent-connect-aws imports - local package
from tac_aws.connectors import StrandsConnector, BedrockAgentCoreConnector
from tac_aws.proxy import AgentCoreLambdaProxy, TwilioSignatureValidator
from tac_aws.server import TACAgentCoreApp, TACAWSFastAPIServer
```

### Incorrect Imports (DO NOT DO)

```python
# ❌ Wrong - the top-level package only exposes __version__
from tac_aws import StrandsConnector

# ❌ Wrong - TAC classes live in tac, not tac_aws
from tac_aws.core import TAC
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

Tests live in `tests/` and use pytest with `asyncio_mode = auto` (see `pytest.ini`). Run with `make test` or `uv run pytest`. Tests should:
- Import from `tac_aws` (local) and `tac` (external dependency)
- Mock AWS clients with pytest fixtures rather than calling AWS APIs
- Cover connector routing and server initialization

CI's `TAC Compat` matrix also runs lint, mypy and tests against the latest patch of each `twilio-agent-connect` minor in the `pyproject.toml` range (`.github/scripts/tac_versions.py`), so code must work on the oldest supported minor, not just the locked one. The matrix runs on Python 3.10, the oldest version this package supports. Reproduce and fix steps: CONTRIBUTING.md, "SDK Compatibility Checks".

## Updating TAC Dependency

When a new `twilio-agent-connect` release is published to PyPI, bump every `twilio-agent-connect` constraint in `pyproject.toml` together (base dependency and each extra that pulls it), then re-lock and run all checks:

```bash
make sync
make check
```

Raising the lower bound drops older minors from the `TAC Compat` matrix, so only raise it when code needs a newer TAC feature.

## Documentation

- The public API reference is published at https://twilio.github.io/twilio-agent-connect-aws/, versioned with `mike` and deployed from `.github/workflows/docs.yml` on each GitHub release.
- API docs are generated from docstrings by MkDocs Material + mkdocstrings, so **docstrings are published documentation**. Write them for both source readers and the rendered site.
- Use **Markdown** in docstrings: `**bold**`, `- ` bullet lists, backticks for identifiers, and fenced code blocks for examples, with a blank line before a list or fenced block.
- TAC core types (`TAC`, `ConversationSession`, ...) resolve to the TAC Python docs via the `inventories` entry in `mkdocs.yml`, so annotating with real TAC types produces cross-repo links.
- `docs/api/proxy.md` and `docs/api/server.md` target individual modules, not their packages: `tac_aws/proxy/__init__.py` and `tac_aws/server/__init__.py` build `__all__` at runtime inside `try/except ModuleNotFoundError`, which griffe cannot resolve statically. When you add a module to either package, add it to the matching docs page.
- `docs/index.md` and `docs/deploy/*.md` are one-line snippet includes of `README.md` and the `deploy/*/README.md` guides. Edit the source Markdown, never the stub, and use absolute GitHub URLs for repo-only paths in those files.
- Verify docs changes with `make docs` (`uv run --group docs mkdocs build --strict`).

## Common Pitfalls

1. **Don't import connectors from `tac_aws`** - use `tac_aws.connectors`.
2. **Don't copy TAC source code** - TAC is a dependency, not vendored.
3. **Don't pass `None` channels to a server** - `connector.rcs` and `connector.whatsapp` are `None` when not configured; use `connector.channels.messaging`.
4. **Connectors own the channels** - don't create separate channel instances for them.
5. **Optional dependencies are gated** - each runtime needs its own extra installed; the proxy requires `agentcore`, the server requires `server`.

## Related Documentation

- TAC Core: [twilio-agent-connect-python](https://github.com/twilio/twilio-agent-connect-python)
- TAC Google sibling: [twilio-agent-connect-google](https://github.com/twilio/twilio-agent-connect-google)
- TAC Microsoft sibling: [twilio-agent-connect-microsoft](https://github.com/twilio/twilio-agent-connect-microsoft)
- AWS Strands: [strandsagents.com/docs](https://strandsagents.com/docs)
- AWS Bedrock: [docs.aws.amazon.com/bedrock](https://docs.aws.amazon.com/bedrock/)
- Examples: `getting_started/examples/`
- Deployment: `deploy/README.md`
- Published API reference: [twilio.github.io/twilio-agent-connect-aws](https://twilio.github.io/twilio-agent-connect-aws/)
