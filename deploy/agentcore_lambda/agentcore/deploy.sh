#!/bin/bash
set -e

# Load environment variables from parent .env file first
if [ -f ../.env ]; then
    export $(grep -v '^#' ../.env | xargs)
else
    echo "❌ Error: .env file not found in parent directory"
    exit 1
fi

echo "🚀 Deploying TAC Agent to AgentCore..."
echo "📋 Using AWS Profile: $AWS_PROFILE"
echo "📋 Using AWS Region: $AWS_REGION"
echo "📋 Using S3 Bucket: $S3_BUCKET"

# Check required variables
if [ -z "$S3_BUCKET" ]; then
    echo "❌ Error: S3_BUCKET not set in .env file"
    exit 1
fi

# Create .bedrock_agentcore.yaml from template if it doesn't exist
if [ ! -f .bedrock_agentcore.yaml ]; then
    if [ -f .bedrock_agentcore.yaml.template ]; then
        cp .bedrock_agentcore.yaml.template .bedrock_agentcore.yaml
        # Update s3_path to use deployment bucket from .env
        sed -i '' "s|s3_auto_create: true|s3_path: s3://${S3_BUCKET}/deployments\n      s3_auto_create: false|g" .bedrock_agentcore.yaml
    else
        echo "❌ Error: .bedrock_agentcore.yaml.template not found"
        exit 1
    fi
fi

# Check required Twilio parameters
if [ -z "$TWILIO_ACCOUNT_SID" ] || [ -z "$TWILIO_AUTH_TOKEN" ] || \
   [ -z "$TWILIO_API_KEY" ] || [ -z "$TWILIO_API_SECRET" ] || \
   [ -z "$TWILIO_PHONE_NUMBER" ] || [ -z "$TWILIO_CONVERSATION_CONFIGURATION_ID" ]; then
    echo "❌ Error: Required Twilio environment variables not set in .env file"
    exit 1
fi

# Deploy to AgentCore with environment variables
agentcore deploy \
  --auto-update-on-conflict \
  --env TWILIO_ACCOUNT_SID=$TWILIO_ACCOUNT_SID \
  --env TWILIO_AUTH_TOKEN=$TWILIO_AUTH_TOKEN \
  --env TWILIO_API_KEY=$TWILIO_API_KEY \
  --env TWILIO_API_SECRET=$TWILIO_API_SECRET \
  --env TWILIO_PHONE_NUMBER=$TWILIO_PHONE_NUMBER \
  --env TWILIO_CONVERSATION_CONFIGURATION_ID=$TWILIO_CONVERSATION_CONFIGURATION_ID \
  --env TWILIO_LOG_LEVEL=${TWILIO_LOG_LEVEL:-DEBUG}

echo ""
echo "✅ AgentCore deployment complete!"
