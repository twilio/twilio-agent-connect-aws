# TAC AWS Deployment Guide

Production deployment options for TAC AWS connectors.

## Available Deployments

### AWS Fargate with Strands

Deploy Strands SDK-based agents to AWS Fargate with Application Load Balancer.

**Guide:** [`strands_aws_fargate/README.md`](strands_aws_fargate/README.md)

**Includes:**
- ECS Fargate + ALB infrastructure
- Docker build process
- Complete CloudFormation templates
- Architecture diagrams with Mermaid
- Production configuration
- Multi-stage Docker build for private dependencies

**Best for:**
- Production Strands agents
- Scalable multi-channel deployments (SMS + Voice)
- AWS-native infrastructure

## Deployment Options

### Strands Connector

Use the Strands AWS Fargate deployment for agents built with the Strands SDK. The deployment includes everything needed to run a production TAC Server with StrandsConnector.

### Bedrock AgentCore Connector

For Bedrock AgentCore deployments, agents are deployed directly to AWS AgentCore runtime endpoints. The connector invokes these pre-deployed agents via `invoke_agent_runtime()` API calls - no separate TAC server deployment to AgentCore is needed. You can deploy the TAC Server with BedrockAgentCoreConnector using similar patterns to the Strands Fargate deployment.

## Getting Started

1. Choose your connector type (Strands or Bedrock AgentCore)
2. Follow the appropriate deployment guide
3. Configure environment variables
4. Deploy infrastructure

For local development and testing, see [`../getting_started/README.md`](../getting_started/README.md)
