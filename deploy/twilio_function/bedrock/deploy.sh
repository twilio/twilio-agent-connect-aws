#!/bin/bash
set -e

echo "🚀 Deploying Twilio Function (TAC + Bedrock)..."
echo ""

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "❌ Error: .env file not found"
    echo ""
    echo "Create .env file:"
    echo "  cp .env.example .env"
    echo "  # Edit .env with your values"
    exit 1
fi

# Validate required variables
REQUIRED_VARS=(
    "TWILIO_ACCOUNT_SID"
    "TWILIO_AUTH_TOKEN"
    "TWILIO_API_KEY"
    "TWILIO_API_SECRET"
    "TWILIO_PHONE_NUMBER"
    "BEDROCK_AGENT_ID"
    "AWS_REGION"
    "AWS_ACCESS_KEY_ID"
    "AWS_SECRET_ACCESS_KEY"
)

MISSING_VARS=()
for VAR in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!VAR}" ]; then
        MISSING_VARS+=("$VAR")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo "❌ Missing required environment variables in .env:"
    for VAR in "${MISSING_VARS[@]}"; do
        echo "  - $VAR"
    done
    exit 1
fi

echo "✓ Environment validated"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
npm install --silent

echo "✓ Dependencies installed"
echo ""

# Create env file for twilio-run. ACCOUNT_SID/AUTH_TOKEN are Twilio Function
# reserved vars; the rest are passed through to the handler via `context`.
cat > .env.deploy <<EOF
ACCOUNT_SID=${TWILIO_ACCOUNT_SID}
AUTH_TOKEN=${TWILIO_AUTH_TOKEN}
TWILIO_API_KEY=${TWILIO_API_KEY}
TWILIO_API_SECRET=${TWILIO_API_SECRET}
TWILIO_PHONE_NUMBER=${TWILIO_PHONE_NUMBER}
TWILIO_REGION=${TWILIO_REGION}
BEDROCK_AGENT_ID=${BEDROCK_AGENT_ID}
BEDROCK_AGENT_ALIAS_ID=${BEDROCK_AGENT_ALIAS_ID:-TSTALIASID}
AWS_REGION=${AWS_REGION}
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
DEBUG=${DEBUG}
EOF

echo "✓ Created deployment env file"
echo ""

echo "☁️  Deploying to Twilio..."
echo ""

SERVICE_NAME="${SERVICE_NAME:-tac-bedrock}"

npx twilio-run deploy \
  --service-name "$SERVICE_NAME" \
  --environment prod \
  --override-existing-project \
  --env .env.deploy \
  > /tmp/twilio-bedrock-deploy-output.log 2>&1

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Deployment failed"
    cat /tmp/twilio-bedrock-deploy-output.log
    rm -f .env.deploy
    exit 1
fi

cat /tmp/twilio-bedrock-deploy-output.log
rm -f .env.deploy

DOMAIN=$(grep -o 'https://[^/]*\.twil\.io' /tmp/twilio-bedrock-deploy-output.log | head -1 | sed 's|https://||')

echo ""
echo "✅ Twilio Function deployment complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📞 Conversation Webhook URL (SMS):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  https://${DOMAIN}/handler?route=webhook"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📞 Voice Webhook URL (A CALL COMES IN):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  https://${DOMAIN}/handler?route=voice"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Configure the SMS URL in Twilio Console → Conversation Orchestrator,"
echo "and the Voice URL on your phone number → Voice → 'A CALL COMES IN'."
echo "To update: Run ./deploy.sh again"
