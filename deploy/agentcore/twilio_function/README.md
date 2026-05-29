# TAC AgentCore - Twilio Function Deployment

Deploy Twilio Function webhook proxy for Twilio Agent Connect with AgentCore.

## Overview

**Components:**
- **Twilio Function** - Serverless webhook handler (`/handler?route=twiml`, `/handler?route=webhook`)
- **IAM User** - Access keys for Twilio Function to call AgentCore (runs outside AWS)

**Security:**
- The function uses **"protected" visibility**, which means Twilio automatically validates the `X-Twilio-Signature` header on all requests
- Only Twilio webhooks can access the function - public access is blocked

**How it works:**
- Voice: Twilio Function generates TwiML → Twilio ConversationRelay connects to AgentCore via WebSocket
- SMS: Twilio Function forwards webhooks → AgentCore processes and responds via Conversations API

## Architecture

```mermaid
graph TB
    Customer([👤 Customer<br/>Phone Call / SMS])

    subgraph Twilio["☁️ Twilio Cloud"]
        Phone[📱 Phone Number<br/>+1-XXX-XXX-XXXX]
        TwilioFunc[⚡ Twilio Function<br/>Node.js Serverless]
        Maestro[💬 Conversations<br/>Maestro API]
        Memory[🧠 Memory Service<br/>Profile & Context]
    end

    subgraph AWS["☁️ AWS Account"]
        subgraph AgentCore["🤖 Bedrock AgentCore Runtime"]
            Agent[🧠 TAC AWS<br/>Omni Channel<br/>WebSocket/HTTP]
        end
    end

    %% Voice Channel Flow (A-D)
    Customer -->|A. Phone Call| Phone
    Phone -->|B. POST /handler?route=twiml| TwilioFunc
    TwilioFunc -->|C. TwiML with<br/>pre-signed WebSocket URL| Phone
    Phone <-->|D. Twilio ConversationRelay| Agent
    
    %% Messaging Channel Flow (1-4)
    Customer -->|1. SMS| Phone
    Phone -->|2. POST /handler?route=webhook| TwilioFunc
    TwilioFunc -->|3. Forward Webhook| Agent
    Agent -->|4. SMS Response| Phone
    
    %% AgentCore integrations
    Agent --> Maestro
    Agent --> Memory
    
    Phone -->|Response| Customer

    style Customer fill:#e1f5ff
    style Twilio fill:#f0f0f0
    style AWS fill:#fff4e6
    style TwilioFunc fill:#fff9c4
    style AgentCore fill:#f3e5f5
    style Agent fill:#e1bee7
```

## Prerequisites

- **AgentCore runtime deployed** - Get the `AGENTCORE_RUNTIME_ARN` from agent deployment
- **AWS credentials configured** - For creating IAM user
- **Twilio CLI installed** - `npm install -g twilio-cli`
- **Twilio CLI logged in** - `twilio login`
- **Node.js 18+** - For CDK and Twilio Functions
- **CDK bootstrapped** - See [parent README](../README.md#bootstrap-cdk-one-time-setup)

## Environment Variables

Create a `.env` file in this directory:

```bash
cp .env.example .env
# Edit .env with your values
```

**Required variables:**

```bash
# AgentCore Runtime ARN (from agent deployment output)
AGENTCORE_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/tacagent-xxxxx

# Twilio Configuration
TWILIO_ACCOUNT_SID=ACxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_CONVERSATION_CONFIGURATION_ID=WRxxxx

# AWS Configuration
AWS_REGION=us-east-1

# AWS IAM Credentials (populated after Step 1)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
```

## Deployment

### Step 1: Deploy IAM User

Create IAM user with access keys for Twilio Functions:

```bash
cd cdk
AWS_PROFILE=your-profile npx cdk deploy
```

**Expected output:**

```
Outputs:
TacAgentcoreTwilioFunctionStack.AccessKeyId = AKIAXXXXXXXXXXXXXXXX
TacAgentcoreTwilioFunctionStack.SecretAccessKey = xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TacAgentcoreTwilioFunctionStack.UserName = tac-agentcore-twilio-function-user
TacAgentcoreTwilioFunctionStack.Warning = The Secret Access Key is only visible once...
```

⚠️ **Important:** The secret access key is only shown once. Copy it immediately!

**Update `.env`:**

Copy the access keys to `../.env`:

```bash
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Step 2: Deploy Twilio Function

```bash
cd ../function
./deploy.sh
```

**What the script does:**
1. Validates environment variables
2. Installs Node.js dependencies
3. Deploys to Twilio using `twilio-run`
4. Outputs webhook URLs

**Expected output:**

```
✅ Twilio Function deployment complete!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📞 Webhook URLs:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VoiceWebhookUrl:
  https://tac-agentcore-xxxx.twil.io/handler?route=twiml

ConversationWebhookUrl:
  https://tac-agentcore-xxxx.twil.io/handler?route=webhook

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Twilio Configuration

### 1. Configure Voice Webhook (Phone Number)

Configure voice calls to use the Twilio Function webhook:

1. Go to Twilio Console → Phone Numbers → Active Numbers
2. Select your phone number
3. Under "Voice Configuration":
   - **A CALL COMES IN:** Webhook
   - **URL:** Use the `VoiceWebhookUrl` from deployment output
   - **HTTP Method:** POST
4. Save

### 2. Configure Conversation Webhook (Conversation Orchestrator)

Configure SMS/messaging to use the Twilio Function webhook:

1. Go to Twilio Console → Conversation Orchestrator
2. Select your Conversation Configuration
3. Under "Webhook Configuration":
   - **Webhook URL:** Use the `ConversationWebhookUrl` from deployment output
   - **HTTP Method:** POST
4. Save

## Project Structure

```
twilio_function/
├── .env                # Configuration (create from .env.example)
├── .env.example        # Template
├── cdk/                # CDK infrastructure for IAM user (TypeScript)
│   ├── bin/
│   │   ├── cdk.ts              # CDK entry point
│   │   └── env-config.ts       # Environment loader
│   ├── lib/
│   │   └── cdk-stack.ts        # IAM user stack
│   └── package.json
├── function/           # Twilio Function code (Node.js)
│   ├── functions/
│   │   └── handler.js          # Webhook handler
│   ├── package.json
│   ├── deploy.sh               # Deployment script
│   └── README.md
└── README.md           # This file
```

