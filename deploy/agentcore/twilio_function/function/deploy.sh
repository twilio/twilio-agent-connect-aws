#!/bin/bash
set -e

echo "🚀 Deploying Twilio Function..."
echo ""

# Load environment variables from parent .env file
if [ -f ../.env ]; then
    export $(grep -v '^#' ../.env | xargs)
else
    echo "❌ Error: .env file not found"
    echo ""
    echo "Create .env file:"
    echo "  cd .."
    echo "  cp .env.example .env"
    echo "  # Edit .env with your values"
    exit 1
fi

# Validate required variables
REQUIRED_VARS=(
    "AWS_REGION"
    "AWS_ACCESS_KEY_ID"
    "AWS_SECRET_ACCESS_KEY"
    "AGENTCORE_RUNTIME_ARN"
    "TWILIO_CONVERSATION_CONFIGURATION_ID"
    "TWILIO_ACCOUNT_SID"
    "TWILIO_AUTH_TOKEN"
)

MISSING_VARS=()
for VAR in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!VAR}" ]; then
        MISSING_VARS+=("$VAR")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo "❌ Missing required environment variables in ../.env:"
    for VAR in "${MISSING_VARS[@]}"; do
        echo "  - $VAR"
    done
    echo ""
    if [[ " ${MISSING_VARS[@]} " =~ " AWS_ACCESS_KEY_ID " ]] || [[ " ${MISSING_VARS[@]} " =~ " AWS_SECRET_ACCESS_KEY " ]]; then
        echo "To create IAM credentials, run:"
        echo "  cd ../cdk && cdk deploy"
    fi
    exit 1
fi

echo "✓ Environment validated"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
npm install --silent

echo "✓ Dependencies installed"
echo ""

# Create .env file for twilio-run
cat > .env <<EOF
ACCOUNT_SID=${TWILIO_ACCOUNT_SID}
AUTH_TOKEN=${TWILIO_AUTH_TOKEN}
AWS_REGION=${AWS_REGION}
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
AGENTCORE_RUNTIME_ARN=${AGENTCORE_RUNTIME_ARN}
TWILIO_CONVERSATION_CONFIGURATION_ID=${TWILIO_CONVERSATION_CONFIGURATION_ID}
EOF

echo "✓ Created .env for deployment"
echo ""

# Deploy using twilio-run
echo "☁️  Deploying to Twilio..."
echo ""

SERVICE_NAME="${SERVICE_NAME:-tac-agentcore}"

# Temporarily disable exit-on-error to capture deployment output
set +e
npx twilio-run deploy \
  --service-name "$SERVICE_NAME" \
  --environment prod \
  --override-existing-project \
  --env .env \
  > /tmp/twilio-deploy-output.log 2>&1
DEPLOY_EXIT_CODE=$?
set -e

# Check if deployment succeeded
if [ $DEPLOY_EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ Deployment failed"
    cat /tmp/twilio-deploy-output.log
    exit 1
fi

# Display deployment output
cat /tmp/twilio-deploy-output.log

# Extract domain from output
DOMAIN=$(grep -o 'https://[^/]*\.twil\.io' /tmp/twilio-deploy-output.log | head -1 | sed 's|https://||')

echo ""
echo "✅ Twilio Function deployment complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📞 Webhook URLs:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "VoiceWebhookUrl:"
echo "  https://${DOMAIN}/handler?route=twiml"
echo ""
echo "ConversationWebhookUrl:"
echo "  https://${DOMAIN}/handler?route=webhook"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To update: Run ./deploy.sh again"
