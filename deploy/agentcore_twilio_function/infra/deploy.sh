#!/bin/bash
set -e

echo "=========================================="
echo "IAM User CloudFormation Deployment"
echo "=========================================="

# Load environment variables from parent .env file
if [ -f ../.env ]; then
    export $(grep -v '^#' ../.env | xargs)
else
    echo "❌ Error: ../.env file not found"
    exit 1
fi

# Check required variables
if [ -z "$AWS_PROFILE" ]; then
    echo "❌ Missing required environment variable: AWS_PROFILE"
    exit 1
fi

STACK_NAME="tac-agentcore-twilio-function-iam"

echo ""
echo "Creating IAM user stack: $STACK_NAME"
echo "AWS Profile: $AWS_PROFILE"
echo ""

# Create stack
aws cloudformation create-stack \
  --stack-name "$STACK_NAME" \
  --template-body file://cloudformation.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --profile "$AWS_PROFILE"

echo "✓ Stack creation initiated"
echo ""
echo "Waiting for stack creation to complete..."

# Wait for stack creation
aws cloudformation wait stack-create-complete \
  --stack-name "$STACK_NAME" \
  --profile "$AWS_PROFILE"

echo "✓ Stack created successfully"
echo ""
echo "=========================================="
echo "IAM Credentials"
echo "=========================================="

# Get outputs
aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].Outputs[?OutputKey==`AccessKeyId`].OutputValue' \
  --output text \
  --profile "$AWS_PROFILE" > /tmp/access_key.txt

aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].Outputs[?OutputKey==`SecretAccessKey`].OutputValue' \
  --output text \
  --profile "$AWS_PROFILE" > /tmp/secret_key.txt

ACCESS_KEY=$(cat /tmp/access_key.txt)
SECRET_KEY=$(cat /tmp/secret_key.txt)

echo ""
echo "AWS_ACCESS_KEY_ID=$ACCESS_KEY"
echo "AWS_SECRET_ACCESS_KEY=$SECRET_KEY"
echo ""
echo "⚠️  IMPORTANT: Copy these credentials to ../.env file:"
echo ""
echo "AWS_ACCESS_KEY_ID=$ACCESS_KEY"
echo "AWS_SECRET_ACCESS_KEY=$SECRET_KEY"
echo ""
echo "These credentials will only be shown once!"
echo "=========================================="

# Cleanup temp files
rm -f /tmp/access_key.txt /tmp/secret_key.txt
