# Twilio Functions - AgentCore Integration

Alternative deployment using Twilio Functions instead of AWS Lambda for webhook handling.

## Overview

Single Twilio Function that routes requests to handle both voice and SMS:

- **`/handler?route=twiml`** - Voice calls (generates TwiML with pre-signed WebSocket URL)
- **`/handler?route=webhook`** - SMS conversations (forwards to AgentCore)

**Architecture:**
```
Customer → Twilio Phone Number → Twilio Function → AWS Bedrock AgentCore
```

---

## Prerequisites

- ✅ AWS account with deployed AgentCore runtime (see `../agentcore/`)
- ✅ Twilio account with phone number and Conversation Configuration ID
- ✅ Node.js 18+ installed

---

## Deployment

### Step 1: Install Twilio CLI

```bash
# macOS
brew tap twilio/brew && brew install twilio

# npm
npm install -g twilio-cli

# Install serverless plugin
twilio plugins:install @twilio-labs/plugin-serverless

# Login
twilio login
```

### Step 2: Setup IAM Credentials

Create IAM user with minimal permissions:

```bash
cd infra
./deploy.sh
```

This creates a CloudFormation stack with:
- IAM user: `tac-agentcore-twilio-function`
- Minimal policy: `bedrock-agentcore:InvokeAgentRuntime` + `GetRuntime`
- Access keys outputted to console

**Copy credentials to `../.env`:**
```bash
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

### Step 3: Configure Environment

Edit `../.env` (shared with Lambda deployment):

```bash
cd ..
cp .env.example .env
# Edit .env - fill in TWILIO_FUNCTION section
```

**Required variables:**
```bash
# AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...                    # From Step 2
AWS_SECRET_ACCESS_KEY=...                    # From Step 2
AGENTCORE_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-east-1:123:runtime/tacagent-xxxxx

# Twilio
TWILIO_CONVERSATION_CONFIGURATION_ID=conv_configuration_xxxxx
```

### Step 4: Deploy Function

```bash
cd twilio_function
./deploy.sh
```

**Output:**
```
✅ Twilio Function deployment complete!

📞 Webhook URLs:
Voice (TwiML):
  https://tac-agentcore-1234.twil.io/handler?route=twiml

SMS (Webhook):
  https://tac-agentcore-1234.twil.io/handler?route=webhook
```

### Step 5: Configure Twilio Webhooks

**Voice Webhook:**
1. Go to [Phone Numbers](https://console.twilio.com/us1/develop/phone-numbers/manage/incoming)
2. Select your phone number
3. Voice Configuration → A CALL COMES IN:
   - Webhook: `https://tac-agentcore-1234.twil.io/handler?route=twiml`
   - HTTP Method: POST

**SMS Webhook:**
1. Go to [Conversation Orchestrator](https://console.twilio.com/us1/develop/conversations/orchestrator)
2. Select your configuration
3. Webhook URL: `https://tac-agentcore-1234.twil.io/handler?route=webhook`
4. HTTP Method: POST

---

## Project Structure

```
twilio_function/
├── infra/
│   ├── cloudformation.yaml    # IAM user definition
│   └── deploy.sh              # One-time IAM setup
├── functions/
│   └── handler.js             # Unified handler (voice + SMS)
├── deploy.sh                  # Main deployment
├── package.json               # Dependencies
└── README.md                  # This file

Parent directory:
../
└── .env.example               # Environment variables (TWILIO_FUNCTION section)
```

---

## How It Works

### Voice Flow
1. Customer calls Twilio number
2. Twilio sends webhook to `/handler?route=twiml`
3. Function generates pre-signed WebSocket URL from AgentCore
4. Returns TwiML with `<ConversationRelay>` pointing to WebSocket
5. Twilio connects audio stream to AgentCore via WebSocket

### SMS Flow
1. Customer sends SMS to Twilio number
2. Twilio sends webhook to `/handler?route=webhook`
3. Function forwards webhook to AgentCore Runtime
4. AgentCore processes and responds via Twilio Conversations API

---

## Operations

### View Logs

```bash
twilio serverless:logs --tail
```

### Test Locally

```bash
twilio serverless:start
# Access at http://localhost:3000/handler?route=twiml
```

### Redeploy

```bash
./deploy.sh
```

### Rotate IAM Keys

```bash
# Delete existing stack
aws cloudformation delete-stack \
  --stack-name tac-agentcore-twilio-function-iam \
  --region us-east-1 \
  --profile your-profile

# Wait for deletion
aws cloudformation wait stack-delete-complete \
  --stack-name tac-agentcore-twilio-function-iam \
  --region us-east-1 \
  --profile your-profile

# Create new stack
cd infra && ./deploy.sh
```

---

## Comparison to Lambda

| Feature | Twilio Functions | AWS Lambda |
|---------|------------------|------------|
| Runtime | Node.js 22 | Python 3.x |
| Deployment | Twilio CLI | CloudFormation |
| Auth | Access Keys | IAM Roles |
| URLs | `*.twil.io` | `*.lambda-url.*.on.aws` |
| Latency | Lower (same network) | Higher (cross-cloud) |
| Cost | $0.0001/invocation | $0.20/1M requests |

---

## Troubleshooting

### "Missing required environment variables"

**Solution:** Check `../.env` has all variables from TWILIO_FUNCTION section

### "Access Denied" when generating WebSocket URL

**Cause:** IAM permissions insufficient

**Solution:**
1. Verify IAM policy includes `bedrock-agentcore:InvokeAgentRuntime`
2. Check `AGENTCORE_RUNTIME_ARN` is correct
3. Verify credentials in `.env` are active

### Voice call doesn't connect

**Check:**
1. Webhook URL in Phone Number settings is correct
2. Logs show "Generated WebSocket URL"
3. AgentCore runtime is deployed and active

### SMS not responding

**Check:**
1. Webhook URL in Conversation Orchestrator is correct
2. Logs show "Incoming conversation webhook"
3. `TWILIO_CONVERSATION_CONFIGURATION_ID` matches your config

---

## Security Best Practices

1. **Minimal IAM Permissions:** Use CloudFormation template (limits to AgentCore only)
2. **Rotate Keys:** Every 90 days minimum
3. **Monitor CloudTrail:** Watch for unauthorized API calls
4. **Environment Variables:** Never commit `.env` to git
5. **Validate Webhooks:** Consider adding Twilio signature validation in production

---

## Clean Up

Delete IAM user:
```bash
aws cloudformation delete-stack \
  --stack-name tac-agentcore-twilio-function-iam \
  --region us-east-1 \
  --profile your-profile
```

Delete Twilio Function:
```bash
twilio serverless:delete --service-name tac-agentcore
```
