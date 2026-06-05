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
npm install -g @aws/agentcore-cli@0.15
```

**Note:** This deployment was tested with AgentCore CLI 0.15.x. If you encounter issues with newer CLI versions, you may need to update the CDK package version in `agentcore/cdk/package.json` or downgrade the CLI to match.

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

### 3. Install CDK Dependencies

The AgentCore CLI needs TypeScript and CDK dependencies:

```bash
cd agentcore/cdk
npm install
cd ../..
```

### 4. Configure Deployment Targets

The AgentCore CLI requires an `aws-targets.json` file to know where to deploy:

```bash
cp agentcore/aws-targets.json.example agentcore/aws-targets.json
```

This creates an empty array `[]` that the AgentCore CLI will populate during deployment with your AWS account details. The file is gitignored because it contains sensitive AWS account information.

### 5. Deploy

Run from the agent folder (project root):

```bash
AWS_PROFILE=your-profile agentcore deploy
```

After deployment completes, retrieve the Runtime ARN:

```bash
AWS_PROFILE=your-profile agentcore status
```

This will display the deployed runtime information including the Runtime ARN.

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

