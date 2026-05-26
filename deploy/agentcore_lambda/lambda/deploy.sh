#!/bin/bash
set -e

STACK_NAME="tac-proxy"

# Load environment variables from .env file
if [ ! -f ../.env ]; then
    echo "❌ Error: .env file not found"
    echo ""
    echo "Please create .env file with required variables"
    exit 1
fi

echo "Loading environment variables from ../.env file..."
export $(grep -v '^#' ../.env | xargs)

# Use variables from .env
REGION=${AWS_REGION}
PROFILE=${AWS_PROFILE}
S3_BUCKET=${S3_BUCKET}

# Check required parameters
if [ -z "$AWS_REGION" ]; then
    echo "❌ Error: AWS_REGION environment variable is not set"
    echo ""
    echo "Please set it in .env file"
    exit 1
fi

if [ -z "$TWILIO_CONVERSATION_CONFIGURATION_ID" ]; then
    echo "❌ Error: TWILIO_CONVERSATION_CONFIGURATION_ID environment variable is not set"
    echo ""
    echo "Please set it in .env file"
    exit 1
fi

if [ -z "$AGENTCORE_RUNTIME_ID" ]; then
    echo "❌ Error: AGENTCORE_RUNTIME_ID environment variable is not set"
    echo ""
    echo "Please set it in .env file:"
    echo "  AGENTCORE_RUNTIME_ID=tacagent-xxxxx"
    echo ""
    echo "Deploy AgentCore first to get the runtime ID"
    exit 1
fi

echo "🚀 Deploying Lambda Webhook Proxy..."
echo ""

# Create Lambda deployment package
echo "1. Creating Lambda deployment package..."
rm -rf package function.zip
mkdir -p package

# Install dependencies for Linux x86_64 (Lambda runtime platform)
echo "   Installing dependencies for Lambda runtime (Linux x86_64)..."
pip3 install \
  --target ./package \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.13 \
  --only-binary=:all: \
  --upgrade \
  bedrock-agentcore-starter-toolkit \
  twilio-agent-connect

cd package
zip -r ../function.zip . -q
cd ..
zip -g function.zip index.py -q

# Package CloudFormation template
echo "2. Packaging CloudFormation template..."
aws cloudformation package \
  --template-file cloudformation.yaml \
  --s3-bucket $S3_BUCKET \
  --s3-prefix lambda-packages \
  --output-template-file packaged.yaml \
  --region $REGION \
  --profile $PROFILE

# Deploy CloudFormation stack
echo "3. Deploying CloudFormation stack..."
aws cloudformation deploy \
  --template-file packaged.yaml \
  --stack-name $STACK_NAME \
  --parameter-overrides \
    TwilioConversationConfigurationId=$TWILIO_CONVERSATION_CONFIGURATION_ID \
    AgentCoreRuntimeId=$AGENTCORE_RUNTIME_ID \
  --capabilities CAPABILITY_NAMED_IAM \
  --region $REGION \
  --profile $PROFILE

# Get outputs
echo ""
echo "4. Getting stack outputs..."
aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --profile $PROFILE \
  --query 'Stacks[0].Outputs' \
  --output table

# Clean up
rm -rf package function.zip packaged.yaml

echo ""
echo "✅ Lambda deployment complete!"
