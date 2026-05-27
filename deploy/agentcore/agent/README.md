# TAC AgentCore Deployment

This directory contains a Twilio Agent Connect (TAC) deployment using AWS Bedrock AgentCore CLI.

## Overview

- **Runtime**: Strands agent with TAC integration
- **Deployment**: AWS AgentCore CLI (Node.js-based, CDK under the hood)
- **Channels**: Voice (WebSocket) and SMS (HTTP)
- **Configuration**: Single `.env` file at `/deploy/agentcore/.env`

## Project Structure

```
deploy/agentcore/
├── .env                    # Configuration (AWS + Twilio credentials)
├── .env.example            # Template for environment setup
└── agent/
    ├── agentcore/          # AgentCore configuration
    │   ├── agentcore.json  # Runtime config
    │   ├── aws-targets.json # Empty (required by CLI, unused)
    │   └── cdk/            # CDK infrastructure code
    │       ├── bin/
    │       │   ├── cdk.ts          # CDK entry point
    │       │   └── env-config.ts   # Environment variable loader
    │       └── lib/
    │           └── cdk-stack.ts    # CloudFormation stack
    └── app/
        └── agent/          # TAC agent code
            ├── main.py     # TAC + Strands integration
            └── pyproject.toml
```

## Prerequisites

- **Node.js** 20.x or later (for AgentCore CLI)
- **Python 3.10+** and **uv** ([install uv](https://docs.astral.sh/uv/getting-started/installation/))
- **AWS credentials** configured with profile
- **AWS account bootstrapped for CDK** (one-time setup)

## Setup

### 1. Install AgentCore CLI

```bash
npm install -g @aws/agentcore-cli
```

### 2. Configure Environment

Copy the example environment file and fill in your values:

```bash
cp deploy/agentcore/.env.example deploy/agentcore/.env
```

Edit `deploy/agentcore/.env`:

```bash
# AWS Configuration
AWS_ACCOUNT_ID=123456789012
AWS_REGION=us-east-1

# Twilio Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_API_KEY=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_SECRET=your_api_secret
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_CONVERSATION_CONFIGURATION_ID=conv_configuration_xxxxx
TWILIO_LOG_LEVEL=DEBUG
```

### 3. Bootstrap CDK (One-Time)

If you haven't bootstrapped your AWS account for CDK:

```bash
AWS_PROFILE=your-profile npx cdk bootstrap aws://YOUR_ACCOUNT_ID/us-east-1
```

This creates required resources:
- S3 bucket for CDK assets
- ECR repository for container images
- IAM roles for deployment
- SSM parameter for version tracking

### 4. Deploy

From the `agentcore/` directory:

```bash
cd deploy/agentcore/agent/agentcore
AWS_PROFILE=your-profile agentcore deploy
```

Deployment creates:
- CloudFormation stack: `TacAgentCoreCliStack`
- AgentCore runtime: `agent_tacagentcli-XXXXX`
- HTTP and WebSocket endpoints
