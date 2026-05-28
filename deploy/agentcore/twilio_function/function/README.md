# Twilio Function Code

This folder contains the Twilio Function code for proxying webhooks to AgentCore.

## Structure

```
function/
├── functions/
│   └── handler.js          # Main handler (routes /twiml and /webhook)
├── package.json            # Node.js dependencies
├── deploy.sh               # Deployment script
└── README.md               # This file
```

## Prerequisites

- **IAM credentials deployed** - Run `cd ../cdk && cdk deploy` first
- **Twilio CLI installed** - `npm install -g twilio-cli`
- **Twilio CLI logged in** - `twilio login`

## Deployment

```bash
./deploy.sh
```

This will:
1. Read `.env` from parent directory (`../.env`)
2. Validate all required environment variables
3. Install Node.js dependencies
4. Deploy to Twilio using `twilio-run`
5. Output webhook URLs

## Environment Variables

The script reads from `../.env`:

**Required:**
- `AWS_REGION` - AWS region
- `AWS_ACCESS_KEY_ID` - IAM access key (from CDK deployment)
- `AWS_SECRET_ACCESS_KEY` - IAM secret key (from CDK deployment)
- `AGENTCORE_RUNTIME_ARN` - AgentCore runtime ARN
- `TWILIO_CONVERSATION_CONFIGURATION_ID` - Twilio conversation config ID
- `TWILIO_ACCOUNT_SID` - Twilio account SID
- `TWILIO_AUTH_TOKEN` - Twilio auth token

**Optional:**
- `SERVICE_NAME` - Twilio service name (default: tac-agentcore)
- `TWILIO_ENVIRONMENT` - Twilio environment (default: prod)

## Outputs

After deployment:

```
Webhook URLs:
  Voice (TwiML):   https://tac-agentcore-xxxx.twil.io/handler?route=twiml
  Webhook (SMS):   https://tac-agentcore-xxxx.twil.io/handler?route=webhook
```

## Handler Routes

**`/handler?route=twiml`** (Voice)
- Generates pre-signed WebSocket URL
- Returns TwiML with `<ConversationRelay>`
- Used for voice calls

**`/handler?route=webhook`** (SMS)
- Forwards webhook to AgentCore HTTP endpoint
- Uses `InvokeAgentRuntimeCommand`
- Used for SMS/messaging

## Local Development

```bash
# Install dependencies
npm install

# Start local dev server
npm run dev
```

Functions will be available at:
- http://localhost:3000/handler?route=twiml
- http://localhost:3000/handler?route=webhook

## Updating

```bash
# Edit handler.js or package.json
# Then redeploy
./deploy.sh
```

## Troubleshooting

**Error: "Missing AWS_ACCESS_KEY_ID"**
- Deploy IAM user first: `cd ../cdk && cdk deploy`
- Copy outputs to `../.env`

**Error: "Twilio CLI not logged in"**
- Run: `twilio login`

**Error: "Service already exists"**
- The script uses `--override-existing-project` to update existing service
- If issues persist, delete service via Twilio Console and redeploy
