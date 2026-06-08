.PHONY: build deploy deploy-all deploy-agentcore deploy-lambda bootstrap clean help

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
	@echo "  deploy-all       - Deploy both AgentCore and Lambda stacks"
	@echo "  deploy-agentcore - Deploy only AgentCore stack"
	@echo "  deploy-lambda    - Deploy only Lambda stack"
	@echo "  deploy           - Alias for deploy-all"
	@echo "  clean            - Clean build artifacts"
	@echo ""
	@echo "Usage:"
	@echo "  make bootstrap      # One-time setup"
	@echo "  make build deploy   # Deploy"

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

# Deploy all stacks (AgentCore + Lambda)
deploy-all:
ifndef AWS_PROFILE
	$(error AWS_PROFILE is not set in .env file. Add AWS_PROFILE=<your-profile> to deploy/agentcore_aws_lambda/.env)
endif
	@echo "Deploying all stacks (AgentCore + Lambda)..."
	cd cdk && AWS_PROFILE=$(AWS_PROFILE) npx aws-cdk deploy --all --require-approval never
	@echo ""
	@echo "✓ All stacks deployed!"
	@echo ""
	@echo "View stack outputs:"
	@echo "  aws cloudformation describe-stacks --stack-name TacAgentCoreStack --profile $(AWS_PROFILE)"
	@echo "  aws cloudformation describe-stacks --stack-name TacLambdaStack --profile $(AWS_PROFILE)"

# Deploy only AgentCore stack
deploy-agentcore:
ifndef AWS_PROFILE
	$(error AWS_PROFILE is not set in .env file. Add AWS_PROFILE=<your-profile> to deploy/agentcore_aws_lambda/.env)
endif
	@echo "Deploying AgentCore stack..."
	cd cdk && AWS_PROFILE=$(AWS_PROFILE) npx aws-cdk deploy TacAgentCoreStack --require-approval never
	@echo ""
	@echo "✓ AgentCore stack deployed!"

# Deploy only Lambda stack
deploy-lambda:
ifndef AWS_PROFILE
	$(error AWS_PROFILE is not set in .env file. Add AWS_PROFILE=<your-profile> to deploy/agentcore_aws_lambda/.env)
endif
	@echo "Deploying Lambda stack..."
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
