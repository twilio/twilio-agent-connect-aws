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

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --profile $AWS_PROFILE --query Account --output text)

# Create S3 bucket for AgentCore deployments with unique name to avoid global conflicts
S3_BUCKET_NAME="agentcore-deploy-${AWS_ACCOUNT_ID}-${AWS_REGION}"
echo "📦 Checking S3 bucket: $S3_BUCKET_NAME"

if ! aws s3 ls s3://$S3_BUCKET_NAME --profile $AWS_PROFILE --region $AWS_REGION 2>/dev/null; then
    echo "   Creating S3 bucket..."

    # Try to create bucket, if name is taken globally, add random suffix
    if ! aws s3 mb s3://$S3_BUCKET_NAME --profile $AWS_PROFILE --region $AWS_REGION 2>/dev/null; then
        echo "   ⚠️  Bucket name taken globally, trying with random suffix..."
        RANDOM_SUFFIX=$(date +%s | tail -c 6)
        S3_BUCKET_NAME="agentcore-deploy-${AWS_ACCOUNT_ID}-${AWS_REGION}-${RANDOM_SUFFIX}"
        aws s3 mb s3://$S3_BUCKET_NAME --profile $AWS_PROFILE --region $AWS_REGION
    fi

    echo "   ✅ Bucket created: $S3_BUCKET_NAME"
else
    echo "   ✅ Bucket exists: $S3_BUCKET_NAME"
fi

# Create .bedrock_agentcore.yaml from template if it doesn't exist
if [ ! -f .bedrock_agentcore.yaml ]; then
    if [ -f .bedrock_agentcore.yaml.template ]; then
        cp .bedrock_agentcore.yaml.template .bedrock_agentcore.yaml
        # Update s3_path to use our custom bucket
        sed -i '' "s|s3_auto_create: true|s3_path: s3://${S3_BUCKET_NAME}/deployments\n      s3_auto_create: false|g" .bedrock_agentcore.yaml
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
