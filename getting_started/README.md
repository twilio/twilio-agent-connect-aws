# Getting Started with twilio-agent-connect-aws

Quick start guide for using twilio-agent-connect-aws with AWS agent runtimes.

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
# Includes all connectors and development tools
pip install twilio-agent-connect-aws[dev]
```

## Environment Setup

Create a `.env` file with your credentials. See [`examples/.env.example`](examples/.env.example) for a complete template.

### Required (All Examples)

```bash
# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_API_KEY=your_api_key
TWILIO_API_SECRET=your_api_secret
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_CONVERSATION_CONFIGURATION_ID=conv_configuration_xxx

# Voice Channel
TWILIO_VOICE_PUBLIC_DOMAIN=your-domain.ngrok.app
```

### AWS Service Specific

**Bedrock Agents:**
```bash
BEDROCK_AGENT_ID=your_agent_id
BEDROCK_AGENT_ALIAS_ID=TSTALIASID
AWS_REGION=us-east-1
```

**Bedrock AgentCore:**
```bash
BEDROCK_AGENTCORE_AGENT_ARN=arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/agent-xxx
AWS_REGION=us-east-1
```

## Examples

See [`examples/`](examples/) for complete working examples:

- **`strands_agents.py`** - Strands SDK with per-conversation agent management
- **`bedrock_agents.py`** - AWS Bedrock Agents (console-created agents)
- **`bedrock_agentcore_agents.py`** - AWS Bedrock AgentCore (custom agent code deployment)

## Running Examples

```bash
cd getting_started/examples
python strands_agents.py
# or
python bedrock_agents.py
# or
python bedrock_agentcore_agents.py
```

## What Connectors Provide

All connectors handle:
- Multi-channel support (SMS + Voice)
- TAC memory retrieval and injection
- Conversation management
- Response routing
