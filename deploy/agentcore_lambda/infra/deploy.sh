#!/bin/bash
set -e

STACK_NAME="tac-agentcore-lambda-infra"

# Load environment variables from parent .env file
if [ -f ../.env ]; then
    export $(grep -v '^#' ../.env | xargs)
else
    echo "❌ Error: .env file not found in parent directory"
    exit 1
fi

# Check required variables
if [ -z "$S3_BUCKET" ]; then
    echo "❌ Error: S3_BUCKET not set in .env file"
    exit 1
fi

if [ -z "$AWS_PROFILE" ]; then
    echo "❌ Error: AWS_PROFILE not set in .env file"
    exit 1
fi

if [ -z "$AWS_REGION" ]; then
    echo "❌ Error: AWS_REGION not set in .env file"
    exit 1
fi

echo "🚀 Deploying S3 Infrastructure..."
echo "📋 Bucket Name: $S3_BUCKET"
echo "📋 AWS Profile: $AWS_PROFILE"
echo "📋 AWS Region: $AWS_REGION"

# Deploy CloudFormation stack
aws cloudformation deploy \
  --template-file cloudformation.yaml \
  --stack-name $STACK_NAME \
  --parameter-overrides BucketName=$S3_BUCKET \
  --region $AWS_REGION \
  --profile $AWS_PROFILE \
  --no-fail-on-empty-changeset

echo ""
echo "✅ S3 bucket created: $S3_BUCKET"
