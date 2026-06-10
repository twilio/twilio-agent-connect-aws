.PHONY: build deploy deploy-all deploy-secrets deploy-agentcore deploy-lambda bootstrap clean help

# Load environment variables from .env file
-include .env

# Unset AWS_PROFILE from shell environment to force reading from .env only
unexport AWS_PROFILE
AWS_PROFILE := $(shell grep '^AWS_PROFILE=' .env 2>/dev/null | cut -d '=' -f 2-)

# Default target
help:
	@echo "TAC AgentCore + Lambda Deployment"
	@echo ""
	@echo "Available targets:"
	@echo "  bootstrap        - Bootstrap CDK (one-time setup)"
	@echo "  build            - Build agent code and CDK"
	@echo "  deploy           - Build and deploy all stacks (recommended)"
	@echo "  deploy-all       - Build and deploy all stacks (Secrets + AgentCore + Lambda)"
	@echo "  deploy-secrets   - Build and deploy only Secrets stack"
	@echo "  deploy-agentcore - Build and deploy only AgentCore stack"
	@echo "  deploy-lambda    - Build and deploy only Lambda stack"
	@echo "  clean            - Clean build artifacts"
	@echo ""
	@echo "Usage:"
	@echo "  make bootstrap   # One-time setup"
	@echo "  make deploy      # Build and deploy all stacks"

# Bootstrap CDK (one-time setup)
bootstrap:
ifndef AWS_PROFILE
	$(error AWS_PROFILE is not set in .env file. Add AWS_PROFILE=<your-profile> to deploy/agentcore_aws_lambda/.env)
endif
ifndef AWS_ACCOUNT_ID
	$(error AWS_ACCOUNT_ID is not set in .env file)
endif
ifndef AWS_REGION
	$(error AWS_REGION is not set in .env file)
endif
	@echo "Installing CDK dependencies..."
	cd cdk && npm install
	@echo ""
	@echo "Building CDK TypeScript..."
	cd cdk && npm run build
	@echo ""
	@echo "Bootstrapping CDK..."
	cd cdk && AWS_PROFILE=$(AWS_PROFILE) npx cdk bootstrap aws://$(AWS_ACCOUNT_ID)/$(AWS_REGION)
	@echo ""
	@echo "✓ CDK bootstrapped for $(AWS_ACCOUNT_ID) in $(AWS_REGION)"

# Build everything
build:
	@echo "Building Python agent..."
	cd agent && uv sync --frozen
	@echo ""
	@echo "Building CDK..."
	cd cdk && npm install && npm run build

# Deploy all stacks (Secrets + AgentCore + Lambda)
deploy-all: build
ifndef AWS_PROFILE
	$(error AWS_PROFILE is not set in .env file. Add AWS_PROFILE=<your-profile> to deploy/agentcore_aws_lambda/.env)
endif
	@echo "Deploying all stacks (Secrets + AgentCore + Lambda)..."
	cd cdk && AWS_PROFILE=$(AWS_PROFILE) npx aws-cdk deploy --all --require-approval never
	@echo ""
	@echo "✓ All stacks deployed!"
	@echo ""
	@echo "View stack outputs:"
	@echo "  aws cloudformation describe-stacks --stack-name TacSecretsStack --profile $(AWS_PROFILE)"
	@echo "  aws cloudformation describe-stacks --stack-name TacAgentCoreStack --profile $(AWS_PROFILE)"
	@echo "  aws cloudformation describe-stacks --stack-name TacLambdaStack --profile $(AWS_PROFILE)"

# Deploy only Secrets stack
deploy-secrets: build
ifndef AWS_PROFILE
	$(error AWS_PROFILE is not set in .env file. Add AWS_PROFILE=<your-profile> to deploy/agentcore_aws_lambda/.env)
endif
	@echo "Deploying Secrets stack..."
	cd cdk && AWS_PROFILE=$(AWS_PROFILE) npx aws-cdk deploy TacSecretsStack --require-approval never
	@echo ""
	@echo "✓ Secrets stack deployed!"

# Deploy only AgentCore stack
deploy-agentcore: build
ifndef AWS_PROFILE
	$(error AWS_PROFILE is not set in .env file. Add AWS_PROFILE=<your-profile> to deploy/agentcore_aws_lambda/.env)
endif
	@echo "Deploying AgentCore stack..."
	@echo "Note: AgentCore depends on TacSecretsStack. Ensure TacSecretsStack is deployed first."
	cd cdk && AWS_PROFILE=$(AWS_PROFILE) npx aws-cdk deploy TacAgentCoreStack --require-approval never
	@echo ""
	@echo "✓ AgentCore stack deployed!"

# Deploy only Lambda stack
deploy-lambda: build
ifndef AWS_PROFILE
	$(error AWS_PROFILE is not set in .env file. Add AWS_PROFILE=<your-profile> to deploy/agentcore_aws_lambda/.env)
endif
	@echo "Deploying Lambda stack..."
	@echo "Note: Lambda depends on TacSecretsStack and TacAgentCoreStack. Ensure both are deployed first."
	cd cdk && AWS_PROFILE=$(AWS_PROFILE) npx aws-cdk deploy TacLambdaStack --require-approval never
	@echo ""
	@echo "✓ Lambda stack deployed!"

# Alias for deploy-all
deploy: deploy-all

# Clean build artifacts
clean:
	rm -rf agent/.venv
	rm -rf cdk/node_modules
	rm -rf cdk/cdk.out
	rm -rf cdk/dist
	rm -rf cdk/agentcore/.cache
