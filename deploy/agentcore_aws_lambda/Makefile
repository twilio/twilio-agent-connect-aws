.PHONY: build deploy deploy-all deploy-agentcore deploy-lambda bootstrap clean secret-update destroy help

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
	@echo "  secret-update    - Update Secrets Manager with credentials from .env"
	@echo "  destroy          - Destroy all stacks (Lambda, AgentCore, Secrets)"
	@echo "  clean            - Clean build artifacts"
	@echo ""
	@echo "Usage:"
	@echo "  make bootstrap   # One-time setup"
	@echo "  make deploy      # Build, deploy, and update secrets"
	@echo "  make destroy     # Delete all AWS resources"

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

# Update Secrets Manager with credentials from .env (secrets only, not configuration)
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
ifndef AWS_REGION
	$(error AWS_REGION is not set in .env file)
endif
	@echo "Updating Secrets Manager with Twilio credentials from .env..."
	@TWILIO_ACCOUNT_SID="$(TWILIO_ACCOUNT_SID)" \
		TWILIO_AUTH_TOKEN="$(TWILIO_AUTH_TOKEN)" \
		TWILIO_API_KEY="$(TWILIO_API_KEY)" \
		TWILIO_API_SECRET="$(TWILIO_API_SECRET)" \
		python3 -c 'import json, os; print(json.dumps({"TWILIO_ACCOUNT_SID": os.environ["TWILIO_ACCOUNT_SID"], "TWILIO_AUTH_TOKEN": os.environ["TWILIO_AUTH_TOKEN"], "TWILIO_API_KEY": os.environ["TWILIO_API_KEY"], "TWILIO_API_SECRET": os.environ["TWILIO_API_SECRET"]}))' | \
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
	@echo "Step 2/3: Updating Secrets Manager with credentials from .env..."
	@echo "═══════════════════════════════════════════════════════════"
	@$(MAKE) secret-update
	@echo ""
	@echo "═══════════════════════════════════════════════════════════"
	@echo "Step 3/3: Deploying AgentCore and Lambda stacks..."
	@echo "═══════════════════════════════════════════════════════════"
	cd cdk && AWS_PROFILE=$(AWS_PROFILE) npx aws-cdk deploy TacAgentCoreStack TacLambdaStack --require-approval never
	@echo ""
	@echo "✓ All stacks deployed!"

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

# Destroy all stacks (reverse order: Lambda → AgentCore → Secrets)
destroy:
ifndef AWS_PROFILE
	$(error AWS_PROFILE is not set in .env file. Add AWS_PROFILE=<your-profile> to deploy/agentcore_aws_lambda/.env)
endif
	@echo "⚠️  WARNING: This will destroy all stacks and delete all resources!"
	@echo ""
	@echo "Destroying stacks in order: Lambda → AgentCore → Secrets"
	@echo ""
	cd cdk && AWS_PROFILE=$(AWS_PROFILE) npx aws-cdk destroy TacLambdaStack TacAgentCoreStack TacSecretsStack --force
	@echo ""
	@echo "✓ All stacks destroyed!"

# Clean build artifacts
clean:
	rm -rf agent/.venv
	rm -rf agent/__pycache__
	rm -rf lambda/__pycache__
	rm -rf cdk/node_modules
	rm -rf cdk/cdk.out
	rm -rf cdk/dist
	rm -rf cdk/agentcore/.cache
