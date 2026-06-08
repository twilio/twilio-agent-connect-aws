# TAC AgentCore + Lambda Deployment

Deploy Twilio Agent Connect with AWS Bedrock AgentCore and Lambda webhook proxy.

## Architecture

```mermaid
graph TB
    Customer([👤 Customer<br/>Phone Call / SMS])

    subgraph Twilio["☁️ Twilio Cloud"]
        Phone[📱 Phone Number<br/>+1-XXX-XXX-XXXX]
        Maestro[💬 Conversations<br/>Maestro API]
        Memory[🧠 Memory Service<br/>Profile & Context]
    end

    subgraph AWS["☁️ AWS Account"]
        Lambda[⚡ AWS Lambda<br/>Function URL]

        subgraph AgentCore["🤖 Bedrock AgentCore Runtime"]
            Agent[🧠 TAC Agent<br/>WebSocket/HTTP]
        end
    end

    %% Voice Channel Flow (A-D)
    Customer -->|A. Phone Call| Phone
    Phone -->|B. POST /twiml| Lambda
    Lambda -->|C. TwiML with<br/>pre-signed WebSocket URL| Phone
    Phone <-->|D. Twilio ConversationRelay| Agent
    
    %% Messaging Channel Flow (1-4)
    Customer -->|1. SMS| Phone
    Phone -->|2. POST /webhook| Lambda
    Lambda -->|3. Forward Webhook| Agent
    Agent -->|4. SMS Response| Phone
    
    %% AgentCore integrations
    Agent --> Maestro
    Agent --> Memory
    
    Phone -->|Response| Customer

    style Customer fill:#e1f5ff
    style Twilio fill:#f0f0f0
    style AWS fill:#fff4e6
    style Lambda fill:#fff9c4
    style AgentCore fill:#f3e5f5
    style Agent fill:#e1bee7
```

## Deployment Components

- **AgentCore Runtime** - AI agent with TAC integration, HTTP and WebSocket endpoints
- **Lambda Webhook Proxy** - Serverless webhook router with Function URLs

## Prerequisites

### Required Tools

- **[AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)** - Command-line tool for AWS
- **[Node.js 20+](https://nodejs.org/)** - For CDK infrastructure
- **[Python 3.10+](https://www.python.org/downloads/)** - For agent code
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** - Python package manager
- **[Docker](https://docs.docker.com/get-docker/)** - For Lambda packaging (must be running)

### AWS Account Requirements

- **Active AWS Account** with access to:
  - **Bedrock** (Amazon Nova Pro or Claude models)
  - **AgentCore**, **Lambda**, **CloudFormation**, and **IAM**
- **Recommended region:** `us-east-1` (or your preferred region with Bedrock access)

---

## AWS Setup

### 1. Create IAM User and Access Keys

1. Sign in to [AWS Console](https://console.aws.amazon.com)
2. Navigate to **IAM** → **Users**
3. Click **Create user** (or select existing user)
4. **Add permissions:**
   - Click **Add permissions** → **Attach policies directly**
   - Select `AdministratorAccess` (or define specific permissions as needed)
   - Click **Next** → **Create user**
5. Select the user → **Security credentials** tab
6. Under **Access keys**, click **Create access key**
7. Choose use case: **Command Line Interface (CLI)**
8. **Save credentials** (⚠️ secret key only shown once):
   - Access key ID (e.g., `AKIAIOSFODNN7EXAMPLE`)
   - Secret access key

### 2. Configure AWS CLI Profile

```bash
aws configure --profile your-profile-name
```

When prompted, enter:
- **AWS Access Key ID:** Paste the access key from step 1
- **AWS Secret Access Key:** Paste the secret key from step 1
- **Default region name:** `us-east-1` (or your preferred region)
- **Default output format:** `json`

### 3. Verify Configuration

```bash
aws sts get-caller-identity --profile your-profile-name
```

Expected output:
```json
{
    "UserId": "AIDAI...",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-username"
}
```

Save your **Account ID** (e.g., `123456789012`) - you'll need it for the `.env` file.

---

## Quick Start

### 1. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your values:

```bash
# AWS Configuration
AWS_PROFILE=your-profile-name          # Profile name from step 2
AWS_ACCOUNT_ID=123456789012            # Account ID from step 3
AWS_REGION=us-east-1

# Twilio Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_API_KEY=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_SECRET=your_api_secret
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_CONVERSATION_CONFIGURATION_ID=WRxxxx
```

**Where to find Twilio credentials:**
- Account SID & Auth Token: Twilio Console → Account → API Keys & Tokens
- API Key & Secret: Create new API Key
- Conversation Configuration ID: Twilio Console → Conversation Orchestrator

### 2. Bootstrap CDK (One-Time Setup)

⚠️ **Must complete step 1 first** - `make bootstrap` requires `.env` file.

```bash
make bootstrap
```

This installs CDK dependencies and bootstraps your AWS account for CDK deployments.

**Note:** Only needs to be done once per account/region.

### 3. Deploy Everything

```bash
make build deploy
```

This command:
1. Builds the Python agent code
2. Compiles the CDK TypeScript
3. Deploys both AgentCore runtime and Lambda webhook proxy
4. Handles cross-stack references automatically

**Deployment output:**

```
✓ All stacks deployed!

TacLambdaStack.VoiceWebhookUrl = https://xxxxx.lambda-url.us-east-1.on.aws/twiml
TacLambdaStack.ConversationWebhookUrl = https://xxxxx.lambda-url.us-east-1.on.aws/webhook
```

Copy these webhook URLs for Twilio configuration.

---

## Twilio Configuration

### Configure Voice Webhook (Phone Number)

1. Go to **Twilio Console → Phone Numbers → Active Numbers**
2. Select your phone number
3. Under "Voice Configuration":
   - **A CALL COMES IN:** Webhook
   - **URL:** Use the `VoiceWebhookUrl` from stack outputs
   - **HTTP Method:** POST
4. Save

### Configure Conversation Webhook (SMS/Messaging)

1. Go to **Twilio Console → Conversation Orchestrator**
2. Select your Conversation Configuration
3. Under "Webhook Configuration":
   - **Webhook URL:** Use the `ConversationWebhookUrl` from stack outputs
   - **HTTP Method:** POST
4. Save

---

## View Logs

CloudWatch log groups are created after the first invocation (phone call or SMS).

### AgentCore Logs

1. Go to [CloudWatch Console](https://console.aws.amazon.com/cloudwatch/)
2. In the left sidebar, click **Logs** → **Log Management** → **Log groups**
3. In the search box, type: `/aws/bedrock-agentcore/runtimes/tac_tac_agent-`

### Lambda Logs

1. Go to [CloudWatch Console](https://console.aws.amazon.com/cloudwatch/)
2. In the left sidebar, click **Logs** → **Log Management** → **Log groups**
3. In the search box, type: `/aws/lambda/TacLambdaStack-`

---

## Update Code

After editing agent or Lambda code:

```bash
make build deploy
```

