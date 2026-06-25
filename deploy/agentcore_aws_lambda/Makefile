.PHONY: build deploy deploy-all deploy-agentcore deploy-lambda bootstrap clean secret-update help

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
	@echo "  deploy           - Build, deploy all stacks, and update secrets (recommended)"
	@echo "  deploy-all       - Build and deploy all stacks (Secrets, AgentCore, Lambda)"
	@echo "  deploy-agentcore - Build and deploy only AgentCore stack"
	@echo "  deploy-lambda    - Build and deploy only Lambda stack"
	@echo "  secret-update    - Update Secrets Manager with values from .env"
	@echo "  clean            - Clean build artifacts"
	@echo ""
	@echo "Usage:"
	@echo "  make bootstrap   # One-time setup"
	@echo "  make deploy      # Build, deploy, and update secrets"

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
	cd cdk && npm ci
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
	cd cdk && npm ci && npm run build

# Update Secrets Manager with values from .env
secret-update:
ifndef AWS_PROFILE
	$(error AWS_PROFILE is not set in .env file. Add AWS_PROFILE=<your-profile> to deploy/agentcore_aws_lambda/.env)
endif
ifndef TWILIO_ACCOUNT_SID
	$(error TWILIO_ACCOUNT_SID is not set in .env file)
endif
ifndef TWILIO_AUTH_TOKEN
	$(error TWILIO_AUTH_TOKEN is not set in .env file)
endif
ifndef TWILIO_API_KEY
	$(error TWILIO_API_KEY is not set in .env file)
endif
ifndef TWILIO_API_SECRET
	$(error TWILIO_API_SECRET is not set in .env file)
endif
ifndef TWILIO_PHONE_NUMBER
	$(error TWILIO_PHONE_NUMBER is not set in .env file)
endif
ifndef TWILIO_CONVERSATION_CONFIGURATION_ID
	$(error TWILIO_CONVERSATION_CONFIGURATION_ID is not set in .env file)
endif
ifndef AWS_REGION
	$(error AWS_REGION is not set in .env file)
endif
	@echo "Updating Secrets Manager with Twilio credentials and configuration from .env..."
	@python3 -c 'import json, sys; print(json.dumps({ \
		"TWILIO_ACCOUNT_SID": sys.argv[1], \
		"TWILIO_AUTH_TOKEN": sys.argv[2], \
		"TWILIO_API_KEY": sys.argv[3], \
		"TWILIO_API_SECRET": sys.argv[4], \
		"TWILIO_PHONE_NUMBER": sys.argv[5], \
		"TWILIO_CONVERSATION_CONFIGURATION_ID": sys.argv[6] \
	}))' "$(TWILIO_ACCOUNT_SID)" "$(TWILIO_AUTH_TOKEN)" "$(TWILIO_API_KEY)" "$(TWILIO_API_SECRET)" "$(TWILIO_PHONE_NUMBER)" "$(TWILIO_CONVERSATION_CONFIGURATION_ID)" | \
		aws secretsmanager put-secret-value \
			--secret-id tac/twilio-credentials \
			--region $(AWS_REGION) \
			--profile $(AWS_PROFILE) \
			--secret-string file:///dev/stdin > /dev/null
	@echo "✓ Secrets updated successfully!"

# Deploy all stacks in stages (Secrets → Update → AgentCore + Lambda)
deploy-all: build
ifndef AWS_PROFILE
	$(error AWS_PROFILE is not set in .env file. Add AWS_PROFILE=<your-profile> to deploy/agentcore_aws_lambda/.env)
endif
	@echo "═══════════════════════════════════════════════════════════"
	@echo "Step 1/3: Deploying Secrets stack..."
	@echo "═══════════════════════════════════════════════════════════"
	cd cdk && AWS_PROFILE=$(AWS_PROFILE) npx aws-cdk deploy TacSecretsStack --require-approval never
	@echo ""
	@echo "═══════════════════════════════════════════════════════════"
	@echo "Step 2/3: Updating secret with real credentials from .env..."
	@echo "═══════════════════════════════════════════════════════════"
	@$(MAKE) secret-update
	@echo ""
	@echo "═══════════════════════════════════════════════════════════"
	@echo "Step 3/3: Deploying AgentCore and Lambda stacks..."
	@echo "═══════════════════════════════════════════════════════════"
	cd cdk && AWS_PROFILE=$(AWS_PROFILE) npx aws-cdk deploy TacAgentCoreStack TacLambdaStack --require-approval never
	@echo ""
	@echo "✓ All stacks deployed with real credentials!"
	@echo ""
	@echo "View stack outputs:"
	@echo "  aws cloudformation describe-stacks --stack-name TacSecretsStack --profile $(AWS_PROFILE)"
	@echo "  aws cloudformation describe-stacks --stack-name TacAgentCoreStack --profile $(AWS_PROFILE)"
	@echo "  aws cloudformation describe-stacks --stack-name TacLambdaStack --profile $(AWS_PROFILE)"

# Deploy only AgentCore stack
deploy-agentcore: build
ifndef AWS_PROFILE
	$(error AWS_PROFILE is not set in .env file. Add AWS_PROFILE=<your-profile> to deploy/agentcore_aws_lambda/.env)
endif
	@echo "Deploying AgentCore stack..."
	cd cdk && AWS_PROFILE=$(AWS_PROFILE) npx aws-cdk deploy TacAgentCoreStack --require-approval never
	@echo ""
	@echo "✓ AgentCore stack deployed!"

# Deploy only Lambda stack
deploy-lambda: build
ifndef AWS_PROFILE
	$(error AWS_PROFILE is not set in .env file. Add AWS_PROFILE=<your-profile> to deploy/agentcore_aws_lambda/.env)
endif
	@echo "Deploying Lambda stack..."
	cd cdk && AWS_PROFILE=$(AWS_PROFILE) npx aws-cdk deploy TacLambdaStack --require-approval never
	@echo ""
	@echo "✓ Lambda stack deployed!"

# Deploy and update secrets (recommended workflow)
# Note: deploy-all now handles secret-update in the correct order automatically
deploy: deploy-all

# Clean build artifacts
clean:
	rm -rf agent/.venv
	rm -rf cdk/node_modules
	rm -rf cdk/cdk.out
	rm -rf cdk/dist
	rm -rf cdk/agentcore/.cache
