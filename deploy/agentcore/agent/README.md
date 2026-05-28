# TAC AgentCore Agent Deployment

Deploy the AgentCore runtime with Strands agent and TAC integration.

## Overview

This deploys the core agent runtime that handles conversation logic. After deploying this, you'll need to deploy a webhook proxy (AWS Lambda or Twilio Function) to connect Twilio to the agent.

**What gets deployed:**
- AgentCore Runtime (Strands + TAC)
- HTTP and WebSocket endpoints for agent communication
- CloudWatch logs for monitoring

## Prerequisites

- **Node.js 20+** - For AgentCore CLI
- **Python 3.10+** and **uv** - For agent code ([install uv](https://docs.astral.sh/uv/getting-started/installation/))
- **AWS credentials** configured with profile
- **AWS account** with:
  - Bedrock model access (Amazon Nova Pro or Claude)
  - IAM permissions for AgentCore and CloudFormation
  - Region: us-east-1 (or your preferred region)
- **CDK bootstrapped** - See [parent README](../README.md#bootstrap-cdk-one-time-setup)

## Setup

### 1. Install AgentCore CLI

```bash
npm install -g @aws/agentcore-cli
```

### 2. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```bash
# AWS Configuration
AWS_ACCOUNT_ID=123456789012
AWS_REGION=us-east-1
# AWS_PROFILE=default  # Optional: if using non-default profile

# Twilio Account Credentials
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token

# Twilio API Credentials (for TAC ConversationClient)
TWILIO_API_KEY=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_SECRET=your_api_secret

# Twilio Phone Number
TWILIO_PHONE_NUMBER=+1234567890

# Twilio Conversation Configuration ID
TWILIO_CONVERSATION_CONFIGURATION_ID=WRxxxx

# Optional: Twilio Log Level (DEBUG, INFO, WARNING, ERROR)
# TWILIO_LOG_LEVEL=INFO
```

**Where to find Twilio credentials:**
- Account SID & Auth Token: Twilio Console → Account → API Keys & Tokens
- API Key & Secret: Create API Key
- Conversation Configuration ID: Twilio Console → Conversation Orchestrator

### 3. Deploy

```bash
cd agentcore
AWS_PROFILE=your-profile agentcore deploy
```

**Expected output:**

```
✅ AgentCore deployment complete!

Runtime ARN: arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/agent_tacagentcli-XXXXX
HTTP Endpoint: https://xxxxx.agentcore.us-east-1.amazonaws.com
WebSocket Endpoint: wss://xxxxx.agentcore.us-east-1.amazonaws.com
```

**Save the Runtime ARN** - you'll need it for the webhook proxy deployment (AWS Lambda or Twilio Function).

## Project Structure

```
agent/
├── .env                # Configuration (create from .env.example)
├── .env.example        # Template
├── agentcore/          # AgentCore CLI configuration
│   ├── agentcore.json  # Runtime config
│   └── cdk/            # CDK infrastructure code
│       ├── bin/
│       │   ├── cdk.ts          # CDK entry point
│       │   └── env-config.ts   # Environment loader
│       └── lib/
│           └── cdk-stack.ts    # Stack definition
└── app/
    └── agent/          # TAC agent code
        ├── main.py     # TAC + Strands integration
        └── pyproject.toml
```

## Next Steps

After deploying the agent, deploy a webhook proxy:

**Option 1: AWS Lambda**
```bash
cd ../aws_lambda
# See aws_lambda/README.md
```

**Option 2: Twilio Function**
```bash
cd ../twilio_function
# See twilio_function/README.md
```

