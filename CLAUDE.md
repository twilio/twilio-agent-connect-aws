# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

twilio-agent-connect-aws is an open-source library providing AWS-specific integrations for Twilio Agent Connect (TAC). It contains connectors that combine agent runtime integration with multi-channel conversation management.

**Key Architecture**: twilio-agent-connect-aws is a separate package that depends on TAC as an external dependency. It does NOT contain TAC source code - it imports from the `tac` package.

## Understanding TAC and Twilio Platform Services

TAC (Twilio Agent Connect) is middleware that integrates with several Twilio platform services to enable context-aware AI agents. Understanding these services is essential for using twilio-agent-connect-aws effectively.

### Conversation Orchestrator

**What it is**: Conversation Orchestrator organizes your voice calls, SMS messages, and WhatsApp messages into conversations. It observes traffic from your Twilio account, links it to customer profiles, and makes it available for AI agents and analytics.

**How TAC uses it**: TAC initializes a `ConversationClient` that interacts with Conversation Orchestrator APIs to:
- Create and manage conversations
- Track participants across channels
- List conversation history (communications)
- Link channel IDs (call IDs, message IDs) to conversations
- Retrieve conversation configuration (including memory store ID)

**In twilio-agent-connect-aws**: Connectors use TAC's conversation management to route messages to the appropriate agent instance per conversation. The conversation_id from Orchestrator becomes the session identifier for agent runtimes.

### Conversation Memory

**What it is**: Conversation Memory provides agents with real-time, contextual data about customers. It stores and retrieves key facts, conversation history, preferences, and insights across different channels. This allows agents to build on previous conversations rather than treating every interaction as isolated.

**Key capabilities**:
- **Observations**: Facts and preferences extracted from conversations (e.g., "prefers window seats", "allergic to peanuts")
- **Summaries**: Conversation summaries that provide quick context
- **Sessions**: Historical session data
- **Profile lookup**: Find customer profiles by phone/email

**How TAC uses it**: TAC initializes a `MemoryClient` (using the memory_store_id from Conversation Orchestrator configuration) that:
- Retrieves memories via `retrieve_memory()` with optional semantic search
- Looks up profiles by phone/email when profile_id isn't available
- Provides memory context to your agent callback via `TACMemoryResponse`
- Falls back to Conversation Orchestrator's communication history if Memory API fails

**In twilio-agent-connect-aws**: Connectors inject memory context into agent prompts using `MemoryPromptBuilder`. This context is passed to your agent factory functions, allowing agents to access customer history and preferences automatically.

### Conversation Intelligence

**What it is**: Conversation Intelligence analyzes conversations using language operators to extract insights, detect sentiment, generate summaries, and more. It processes conversations asynchronously and sends results via webhooks.

**How TAC uses it**: TAC includes an `OperatorResultProcessor` that:
- Processes Conversation Intelligence webhook events
- Filters events by configuration ID and operator SID
- Automatically creates observations or summaries in Conversation Memory based on CI results
- Handles multiple operator results per event

**In twilio-agent-connect-aws**: TACFastAPIServer provides optional `/ci-webhook` endpoint for receiving Conversation Intelligence events. Connectors don't directly interact with CI, but they benefit from the observations and summaries that CI creates in Memory.

### Knowledge

**What it is**: Knowledge provides semantic search capabilities over knowledge bases (FAQs, product documentation, company policies, etc.). It enables agents to ground responses in authoritative source material.

**How TAC uses it**: TAC optionally initializes a `KnowledgeClient` that:
- Searches knowledge bases with semantic queries
- Returns relevant chunks with relevance scores
- Provides a `create_knowledge_tool()` for LLM function calling

**In twilio-agent-connect-aws**: You can use TAC's knowledge tools directly in your agent implementations (Strands agents can use `@function_tool` decorated knowledge tools). Knowledge search results can supplement agent context alongside memory.

### How It All Works Together

1. **Conversation starts**: Customer sends SMS or calls → Conversation Orchestrator creates a conversation
2. **TAC retrieves context**: TAC uses conversation_id and profile_id to fetch memories from Conversation Memory
3. **Memory is injected**: TAC provides memory context to your agent (via callback or MemoryPromptBuilder)
4. **Agent responds**: Your agent (Strands, Bedrock, etc.) processes user message with full context
5. **Conversation continues**: Subsequent messages in the same conversation maintain context
6. **Intelligence analyzes**: Conversation Intelligence processes the conversation and creates new observations/summaries
7. **Memory grows**: Future conversations benefit from richer customer profiles

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
│   ├── strands_connector.py               # StrandsConnector (Strands SDK)
│   ├── bedrock_connector.py               # BedrockConnector (Bedrock Agents)
│   └── bedrock_agentcore_connector.py     # BedrockAgentCoreConnector (AgentCore)
└── tools/              # LLM tools for Strands
    └── strands.py                         # Memory tool for Strands agents

getting_started/
└── examples/           # FastAPI server examples
    ├── strands_agents.py
    ├── bedrock_agents.py
    └── bedrock_agentcore_agents.py

deploy/
├── strands_aws_fargate/      # Strands AWS Fargate deployment
├── bedrock_aws_fargate/      # Bedrock Agents AWS Fargate deployment
└── agentcore_aws_fargate/    # AgentCore AWS Fargate deployment
```

## Code Conventions

- **Python 3.10+**: Use `typing` module types (`List`, `Dict`, `Optional`)
- **mypy strict**: All functions need type hints, no incomplete defs
- **ruff**: Line length 100, black-compatible formatting
- **Imports from TAC**: Always import from `tac` package, never from internal `tac_aws` except for local imports

## Dependencies

### Core Dependency

twilio-agent-connect-aws depends on TAC from PyPI:

```toml
dependencies = [
    "twilio-agent-connect>=1.0.0,<2",
]
```

### Optional Dependencies

- `strands` - AWS Strands SDK
- `bedrock` - AWS Bedrock Agents (boto3 + type stubs)
- `agentcore` - AWS Bedrock AgentCore (bedrock-agentcore + boto3 + type stubs)
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

**BedrockConnector:**
- AWS Bedrock Agents integration for console-created agents
- Accepts `tac: TAC`, `invoke_fn: Callable`, and optional channel configs
- User provides invoke function that receives context, user_message, and memory_context
- Invoke function calls `client.invoke_agent()` and returns streaming response
- Connector buffers streaming response and routes to channels
- Uses `sessionId` (conversation_id) for conversation continuity
- Bedrock Agents manage conversation history server-side
- Supports action groups and knowledge bases configured in AWS Console

**BedrockAgentCoreConnector:**
- AWS Bedrock Agent Core integration for custom agent code deployment
- **Base functionality**: `invoke_fn` (required) - HTTP invocation for both voice and SMS
- **Voice optimization**: `websocket_factory` (optional) - WebSocket for low latency (~50ms vs ~200ms)
- **Two different clients**:
  - `boto3.client("bedrock-agentcore")` - provides `invoke_agent_runtime()` for HTTP (required)
  - `AgentCoreRuntimeClient` (from bedrock-agentcore) - provides `generate_ws_connection()` for WebSocket (optional)
- **Voice channel**: WebSocket (if websocket_factory provided) or HTTP streaming (base)
- **SMS channel**: HTTP invocation with response buffering
- Uses `runtimeSessionId` (conversation_id) for conversation continuity
- Deploy custom agent code (Strands, LangGraph, OpenAI SDK, etc.)
- Memory context passed to user's factories on every message
- Supports session manager for voice channel (task cancellation on interrupts)

### Server

twilio-agent-connect-aws uses `TACFastAPIServer` from the core TAC package (`tac.server`):
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

# twilio-agent-connect-aws imports - local package
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
server = TACFastAPIServer(tac=tac, voice_channel=connector.voice, messaging_channels=[connector.sms])
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

### Bedrock Agent with TAC Server

**Simple config-based approach (recommended):**

```python
import boto3
from tac import TAC, TACConfig
from tac.server import TACFastAPIServer
from tac_aws.connectors import BedrockConnector

# Create TAC instance
tac = TAC(config=TACConfig.from_env())

# Create Bedrock Agent Runtime client
client = boto3.client("bedrock-agent-runtime", region_name="us-east-1")

# Simple config - sessionId and inputText auto-injected
connector = BedrockConnector(
    tac=tac,
    bedrock_client=client,
    config={
        "agentId": "AGENT123",
        "agentAliasId": "TSTALIASID",
    }
)

# TAC Server uses connector's channels for HTTP routing
server = TACFastAPIServer(tac=tac, voice_channel=connector.voice, messaging_channels=[connector.sms])
server.start()
```

**Advanced - custom invoke function (for dynamic behavior):**

```python
import boto3
from tac import TAC, TACConfig
from tac.models.session import ConversationSession
from tac.server import TACFastAPIServer
from tac_aws.connectors import BedrockConnector

tac = TAC(config=TACConfig.from_env())
client = boto3.client("bedrock-agent-runtime", region_name="us-east-1")

# Custom invoke function for dynamic logic
def invoke_agent(
    context: ConversationSession,
    user_message: str,
    memory_context: str | None
):
    # Dynamic agent selection based on channel
    agent_id = "VOICE_AGENT" if context.channel == "voice" else "SMS_AGENT"

    full_message = user_message
    if memory_context:
        full_message = f"{memory_context}\n\nUser: {user_message}"

    return client.invoke_agent(
        agentId=agent_id,
        agentAliasId="TSTALIASID",
        sessionId=context.conversation_id,
        inputText=full_message
    )

connector = BedrockConnector(tac=tac, invoke_fn=invoke_agent)
server = TACFastAPIServer(tac=tac, voice_channel=connector.voice, messaging_channels=[connector.sms])
server.start()
```

### Bedrock Agent Core with TAC Server

Uses dual-runtime pattern for maximum flexibility:
- **HTTP invocation** (required): For both voice and SMS channels
- **WebSocket streaming** (optional): For voice channel low-latency optimization (~50ms vs ~200ms)

Users control all parameters via factory functions:
- `factory`: Creates WebSocket connection (called once per session for pooling)
- `payload_fn`: Builds WebSocket message payload (called every message)
- `http`: Invokes agent via HTTP (used by both channels)

```python
import boto3
import json
import websockets
from bedrock_agentcore.runtime import AgentCoreRuntimeClient
from tac import TAC, TACConfig
from tac.channels.sms import SMSChannelConfig
from tac.channels.voice import VoiceChannelConfig
from tac.models.session import ConversationSession
from tac.server import TACFastAPIServer
from tac.session import ThreadSafeSessionManager
from tac_aws.connectors import BedrockAgentCoreConnector
from tac_aws.connectors.bedrock_agentcore.config import RuntimeConfig, WebSocketConfig

# Create TAC instance
tac = TAC(config=TACConfig.from_env())
AGENT_ARN = "arn:aws:bedrock-agentcore:us-east-1:123:agent-runtime/..."

# WebSocket: AgentCoreRuntimeClient provides generate_ws_connection()
agentcore_client = AgentCoreRuntimeClient(region="us-east-1")

async def create_websocket(context: ConversationSession):
    """WebSocket factory - creates connection (called once per session for pooling)."""
    ws_url, headers = agentcore_client.generate_ws_connection(
        runtime_arn=AGENT_ARN,
        session_id=context.conversation_id,
    )
    return await websockets.connect(ws_url, additional_headers=headers)

def build_websocket_payload(
    context: ConversationSession,
    user_message: str,
    memory_context: str | None,
):
    """Build WebSocket message payload (called every message)."""
    payload = {"type": "prompt", "voicePrompt": user_message}
    if memory_context:
        payload["memoryContext"] = memory_context
    return payload

# HTTP: boto3 client provides invoke_agent_runtime()
agentcore_http_client = boto3.client("bedrock-agentcore", region_name="us-east-1")

def invoke_agent_http(
    context: ConversationSession,
    user_message: str,
    memory_context: str | None,
):
    """HTTP invocation for both channels."""
    full_prompt = user_message
    if memory_context:
        full_prompt = f"{memory_context}\n\nUser: {user_message}"

    payload = json.dumps({"prompt": full_prompt}).encode("utf-8")

    return agentcore_http_client.invoke_agent_runtime(
        agentRuntimeArn=AGENT_ARN,
        runtimeSessionId=context.conversation_id,
        payload=payload,
    )

# Create connector
connector = BedrockAgentCoreConnector(
    tac=tac,
    runtime=RuntimeConfig(
        http=invoke_agent_http,  # Required: HTTP streaming for both channels
        websocket=WebSocketConfig(  # Optional: WebSocket optimization for voice
            factory=create_websocket,
            payload_fn=build_websocket_payload,
        ),
    ),
    voice_config=VoiceChannelConfig(
        session_manager=ThreadSafeSessionManager(),
        memory_mode="always",
    ),
    sms_config=SMSChannelConfig(memory_mode="always"),
)

# TAC Server uses connector's channels for HTTP routing
server = TACFastAPIServer(tac=tac, voice_channel=connector.voice, messaging_channels=[connector.sms])
server.start()
```

## Testing

Tests should:
- Import from `tac_aws` package (local)
- Import from `tac` package (external dependency)
- Use pytest fixtures for mocking AWS clients
- Test connector implementations
- Test server initialization and routing

## Updating TAC Dependency

TAC is now available on PyPI. To update to a new version:

```bash
# Update version constraint in pyproject.toml
# dependencies = [
#     "twilio-agent-connect>=1.1.0,<2",  # Update version as needed
# ]

# Sync dependencies
make sync
```

## Common Pitfalls

1. **Don't import from internal tac_aws paths for TAC classes** - use `from tac.X import Y`
2. **Don't copy TAC source code** - TAC is a dependency, not vendored
3. **Don't forget TYPE_CHECKING guards** - for boto3 and strands type hints
4. **Connectors manage both agent runtime and channels** - don't create separate channel instances

## Related Documentation

- TAC Core: [CLAUDE.md](https://github.com/twilio/twilio-agent-connect-python/blob/main/CLAUDE.md)
- AWS Strands: [strandsagents.com/docs](https://strandsagents.com/docs)
- AWS Bedrock: [docs.aws.amazon.com/bedrock](https://docs.aws.amazon.com/bedrock/)
