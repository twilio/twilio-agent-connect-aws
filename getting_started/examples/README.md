# TAC AWS Examples

Examples demonstrating integration with different AWS agent runtimes using OmniChannelFastAPIServer.

## Structure

```
examples/
└── fastapi/           # FastAPI server examples
    ├── strands_agents.py
    ├── bedrock.py
    └── bedrock_agentcore.py
```

## FastAPI Server Examples

All examples use **OmniChannelFastAPIServer** with the adapter pattern.

### Installation
```bash
pip install tac-aws[server] strands-agents boto3
```

### Examples

- **`strands_agents.py`** - Strands SDK (multi-provider: OpenAI, Anthropic, Bedrock)
- **`bedrock.py`** - AWS Bedrock Agent Runtime
- **`bedrock_agentcore.py`** - AWS Bedrock AgentCore service

### Run

```bash
cd fastapi
python strands_agents.py
python bedrock.py
python bedrock_agentcore.py
```

## Architecture

All examples follow the same adapter pattern:

```python
# 1. Create TAC instance
tac = TAC(config=TACConfig.from_env())

# 2. Create AWS agent
agent = Agent(model="gpt-4o")

# 3. Wrap in adapter
adapter = StrandsAdapter(agent)

# 4. Create channel handlers (manages conversation logic)
handlers = OmniChannelHandlers(
    tac=tac,
    adapter=adapter,
    voice=VoiceChannel(tac=tac, auto_retrieve_memory=True),
    sms=SMSChannel(tac=tac, auto_retrieve_memory=True),
)

# 5. Create server (handles HTTP routing)
server = OmniChannelFastAPIServer(handlers=handlers)

# 6. Start
server.start()
```

## Environment Variables

All examples require TAC configuration. See [`../README.md`](../README.md) for setup instructions.

### Required (All Examples)
```bash
# Twilio Configuration
TWILIO_TAC_ACCOUNT_SID=your_account_sid
TWILIO_TAC_AUTH_TOKEN=your_auth_token
TWILIO_TAC_API_KEY=your_api_key          # Starts with SK
TWILIO_TAC_API_TOKEN=your_api_token      # Secret for API key
TWILIO_TAC_PHONE_NUMBER=+1234567890
TWILIO_TAC_CONVERSATION_SERVICE_SID=conv_configuration_xxx

# Server Configuration (for Voice)
TWILIO_TAC_VOICE_PUBLIC_DOMAIN=your-domain.ngrok.io
```

### Additional AWS-Specific Variables

**Bedrock Agent Runtime (`bedrock.py`):**
```bash
AWS_REGION=us-east-1
BEDROCK_AGENT_ID=your-agent-id
BEDROCK_AGENT_ALIAS_ID=TSTALIASID
```

**Bedrock AgentCore (`bedrock_agentcore.py`):**
```bash
AWS_REGION=us-east-1
BEDROCK_AGENTCORE_ARN=arn:aws:bedrock:region:account:agent-runtime/agent-id
BEDROCK_AGENTCORE_QUALIFIER=DEFAULT
```

## Key Features

All examples include:
- ✅ Multi-channel support (SMS + Voice)
- ✅ Automatic memory retrieval and injection
- ✅ Per-conversation history management
- ✅ Automatic response routing
- ✅ WebSocket support for Voice
- ✅ Adapter pattern for easy agent swapping
