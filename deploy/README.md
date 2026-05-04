# aws-twilio-agent-connect Deployment Guide

Production deployment options for aws-twilio-agent-connect connectors.

## Available Deployments

### AWS Fargate with Strands

Deploy Strands SDK-based agents to AWS Fargate with Application Load Balancer.

**Guide:** [`strands_aws_fargate/README.md`](strands_aws_fargate/README.md)

**Includes:**
- ECS Fargate + ALB infrastructure
- Docker multi-stage build
- Complete CloudFormation templates
- Architecture diagrams with Mermaid
- Multi-stage Docker build for private dependencies

**Best for:**
- Production Strands agents with per-conversation management
- Scalable multi-channel deployments (SMS + Voice)

### AWS Fargate with Bedrock Agents

Deploy console-created Bedrock Agents to AWS Fargate with Application Load Balancer.

**Guide:** [`bedrock_aws_fargate/README.md`](bedrock_aws_fargate/README.md)

**Includes:**
- ECS Fargate + ALB infrastructure
- Docker multi-stage build
- Complete CloudFormation templates
- Architecture diagrams with Mermaid
- Integration with console-created Bedrock Agents

**Best for:**
- Console-created Bedrock Agents with action groups and knowledge bases
- Fully managed agent service
- Production multi-channel deployments (SMS + Voice)

### AWS Fargate with Bedrock AgentCore

Deploy Bedrock AgentCore-based agents to AWS Fargate with Application Load Balancer.

**Guide:** [`agentcore_aws_fargate/README.md`](agentcore_aws_fargate/README.md)

**Includes:**
- Agent deployment to Bedrock AgentCore runtime
- TAC Server on ECS Fargate + ALB infrastructure
- Docker multi-stage build
- Complete CloudFormation templates
- Architecture diagrams with Mermaid
- Agent deployment guide with AgentCore CLI

**Best for:**
- Custom agent code deployments (Strands, LangGraph, OpenAI SDK)
- Managed agent runtime with built-in memory
- Pre-deployed agents invoked via API

**Real-world example:**
- [AWS Sample: Bedrock AgentCore + TAC Reference Implementation](https://github.com/aws-samples/sample-bedrock-agentcore-twilio-agent-connect-reference)

## Deployment Architecture

### Strands Connector
TAC Server runs on Fargate and creates per-conversation agent instances using the Strands SDK. Each conversation gets its own agent with isolated state.

### Bedrock Agents Connector
TAC Server runs on Fargate and invokes console-created agents via `invoke_agent()` API. Create agents in AWS Bedrock Console with action groups and knowledge bases. Agents are fully managed by AWS and handle conversation history server-side.

### Bedrock AgentCore Connector
Deploy custom agent code to Bedrock AgentCore runtime. TAC Server on Fargate invokes pre-deployed agents via `invoke_agent_runtime()` API. AgentCore manages runtime and memory.

## Getting Started

1. Choose your connector type
2. Follow the appropriate deployment guide
3. Configure environment variables
4. Deploy infrastructure

For local development and testing, see [`../getting_started/README.md`](../getting_started/README.md)
