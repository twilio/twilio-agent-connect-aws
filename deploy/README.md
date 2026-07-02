# twilio-agent-connect-aws Deployment Guide

Production deployment options for twilio-agent-connect-aws.

## Deployments

### AWS Lambda + Bedrock AgentCore (Recommended)

**Architecture:** Twilio Conversation Relay connects directly to AgentCore via WebSocket. Lambda functions handle Twilio webhooks.

**Key features:**
- Direct WebSocket connection (best performance)
- No Fargate, ALB, or VPC required
- Fully serverless (pay-per-request)
- Single CDK command deployment

**Guide:** [`agentcore_aws_lambda/README.md`](agentcore_aws_lambda/README.md)

**Best for:** Production agents with custom code (Strands, LangGraph, OpenAI SDK)

---

### AWS Fargate + Bedrock AgentCore

**Architecture:** TAC Server runs on Fargate behind ALB. Server connects to AgentCore runtime via HTTP/WebSocket.

**Key features:**
- Custom agent code deployment to AgentCore
- TAC Server on ECS Fargate + ALB
- Docker containerized deployment
- CloudFormation templates

**Guide:** [`agentcore_aws_fargate/README.md`](agentcore_aws_fargate/README.md)

**Best for:** Existing Fargate infrastructure or specific VPC requirements

---

### AWS Fargate + Bedrock Agents

**Architecture:** TAC Server runs on Fargate behind ALB. Server invokes console-created Bedrock Agents via API.

**Key features:**
- Console-created agents with action groups and knowledge bases
- Fully managed agent service
- TAC Server on ECS Fargate + ALB
- CloudFormation templates

**Guide:** [`bedrock_aws_fargate/README.md`](bedrock_aws_fargate/README.md)

**Best for:** Using AWS Bedrock Agents created in AWS Console

---

### AWS Fargate + Strands

**Architecture:** TAC Server runs on Fargate behind ALB. Strands agents created per-conversation with direct Bedrock LLM calls.

**Key features:**
- Strands SDK agent framework
- Per-conversation agent instances
- TAC Server on ECS Fargate + ALB
- CloudFormation templates

**Guide:** [`strands_aws_fargate/README.md`](strands_aws_fargate/README.md)

**Best for:** Strands framework with per-conversation state management
