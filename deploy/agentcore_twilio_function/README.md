# TAC AgentCore - Twilio Function Deployment

Deploy Twilio Agent Connect with AWS Bedrock AgentCore using Twilio Functions.

## Overview

**Components:**
- **Twilio Function**: Serverless webhook handler (`/handler?route=twiml`, `/handler?route=webhook`)
- **AgentCore**: Full TAC server with agent logic
- **Twilio**: Voice/SMS channels with Conversations and Memory

**How it works:**
- Voice: Twilio Function generates TwiML → Twilio ConversationRelay connects to AgentCore via WebSocket
- SMS: Twilio Function forwards webhooks → AgentCore processes and responds via Conversations API

---

## Architecture

### High-Level Architecture

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

---

## AWS Services

### Core Services

| Service | Purpose |
|---------|---------|
| **Bedrock AgentCore Runtime** | Managed agent hosting with built-in memory and observability |
| **AWS IAM User** | Access keys for Twilio Function to call AgentCore (runs outside AWS) |
| **AWS Bedrock** | LLM inference - Amazon Nova Pro, Claude, etc. (pay-per-token) |
| **CloudWatch Logs** | Agent runtime logs |

---

## Deployment

### Prerequisites

**AWS Account:**
- AWS CLI configured with appropriate credentials
- AWS account with:
  - Bedrock model access (Amazon Nova Pro or Claude)
  - IAM permissions for AgentCore and CloudFormation
  - Region: us-east-1 (or your preferred region)

**Twilio Account:**
- Account SID
- Auth Token
- API Key and Secret
- Phone number
- Conversation Configuration ID from Conversation Orchestrator
- Twilio CLI installed and logged in

**Where to find Twilio credentials:**
- Account SID & Auth Token: Twilio Console → Account → API Keys & Tokens
- API Key & Secret: Twilio Console → Account → API Keys & Tokens → Create API Key
- Conversation Configuration ID: Twilio Console → Conversation Orchestrator → Configuration

---

### Step 1: Configure Environment

Copy the example environment file and update with your credentials:

```bash
# From the agentcore_twilio_function directory
cp .env.example .env
```

Edit `.env` with your values:

```bash
# AWS CLI Configuration
AWS_REGION=us-east-1
AWS_PROFILE=your-aws-profile-name

# Twilio Configuration
TWILIO_CONVERSATION_CONFIGURATION_ID=conv_configuration_xxxxx

# AgentCore Configuration [AGENTCORE]
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_API_KEY=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_SECRET=your_api_secret
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_LOG_LEVEL=DEBUG

# AgentCore Runtime ARN - Will be populated after agent deployment
AGENTCORE_RUNTIME_ARN=

# AWS IAM Access Keys - Will be populated after IAM setup
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
```

**Note:** You'll need to update `AGENTCORE_RUNTIME_ARN`, `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY` after Steps 2 and 3.

---

### Step 2: Deploy AgentCore

The `agentcore/` folder contains the agent code ready for deployment.

**Install AgentCore CLI:**

```bash
pip install bedrock-agentcore-starter-toolkit
```

**Deploy the agent:**

```bash
cd agentcore
./deploy.sh
```

**Expected output:**

```
✅ AgentCore deployment complete!
Agent ARN: arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/tacagent-XXXXX
```

**Save the full Agent Runtime ARN:**

Update your `.env` file:

```bash
AGENTCORE_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/tacagent-XXXXX
```

---

### Step 3: Create IAM User

Create an IAM user with permissions for Twilio Function to access AgentCore.

**Deploy IAM stack:**

```bash
cd infra
./deploy.sh
```

**Expected output:**

```
✅ Stack created successfully

========================================
IAM Credentials
========================================

AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

⚠️  IMPORTANT: Copy these credentials to ../.env file
```

**Save the credentials:**

Update your `.env` file:

```bash
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**⚠️ Important:** These credentials are only shown once. If lost, delete and recreate the stack.

---

### Step 4: Deploy Twilio Function

The `twilio_function/` folder contains the Twilio Function webhook handler.

**Verify Twilio CLI is logged in:**

```bash
twilio profiles:list
```

**Deploy Twilio Function:**

```bash
cd twilio_function
./deploy.sh
```

**Expected output:**

```
✅ Twilio Function deployed successfully!

Domain: https://tac-agentcore-xxxx-prod.twil.io

Webhook URLs:
  Voice:   https://tac-agentcore-xxxx-prod.twil.io/handler?route=twiml
  Webhook: https://tac-agentcore-xxxx-prod.twil.io/handler?route=webhook
```

**Save the webhook URLs** - you'll need them for Twilio configuration.

---

### Step 5: Configure Twilio Webhooks

**Voice Webhook (Phone Numbers):**

1. Go to [Twilio Console → Phone Numbers → Active Numbers](https://console.twilio.com/us1/develop/phone-numbers/manage/incoming)
2. Select your phone number
3. Under "Voice Configuration":
   - **A CALL COMES IN:** Webhook
   - **URL:** `https://tac-agentcore-xxxx-prod.twil.io/handler?route=twiml`
   - **HTTP Method:** POST
4. Save

**SMS Webhook (Conversation Orchestrator):**

1. Go to [Twilio Console → Conversation Orchestrator](https://console.twilio.com/us1/develop/conversations/orchestrator)
2. Select your Conversation Service
3. Configure webhook:
   - **Webhook URL:** `https://tac-agentcore-xxxx-prod.twil.io/handler?route=webhook`
   - **HTTP Method:** POST
4. Save
