# TAC Bedrock Agent Server - AWS Fargate Deployment

Complete guide for deploying Twilio Agent Connect (TAC) with AWS Bedrock Agent on AWS Fargate.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [AWS Services](#aws-services)
- [Deployment](#deployment)

---

## Overview

This deployment runs a voice and SMS AI agent using:
- **Twilio** - Voice/SMS communication platform
- **AWS Bedrock Agent** - Fully managed agent with actions, knowledge bases, and guardrails
- **TAC (Twilio Agent Connect)** - Integration middleware

The system handles incoming calls and SMS messages, routes them through an AI agent deployed on AWS Bedrock Agent, and manages conversation state using Twilio's Conversation Orchestrator and Memory services.

---

## Architecture

### High-Level Architecture

```mermaid
graph TB
    Customer([👤 Customer<br/>Phone Call / SMS])

    subgraph Twilio["☁️ Twilio Cloud"]
        Phone[📱 Phone Number<br/>+1-XXX-XXX-XXXX]
        Orchestrator[💬 Conversations<br/>Conversation Orchestrator]
        Memory[🧠 Memory Service<br/>Profile & Context]
    end

    HTTPS[🔒 HTTPS Endpoint<br/>ngrok / CloudFront / Route53<br/>your-domain.example.com]

    subgraph AWS["☁️ AWS Account"]
        ALB[⚖️ Application Load Balancer<br/>TAC-Bedrock-ALB-xxx.elb.amazonaws.com<br/>Port 80 HTTP]

        subgraph VPC["🔐 VPC 10.0.0.0/16"]
            subgraph Subnets["Multi-AZ Public Subnets"]
                Subnet1[📍 Subnet 1<br/>10.0.1.0/24<br/>us-east-1a]
                Subnet2[📍 Subnet 2<br/>10.0.2.0/24<br/>us-east-1b]
            end

            ECS[📦 ECS Fargate Task<br/>TAC Server<br/>BedrockConnector<br/>512 CPU / 1GB RAM<br/>Port 8000]
        end

        subgraph BedrockAgent["🤖 AWS Bedrock Agent"]
            Agent[🧠 Bedrock Agent<br/>Actions, Knowledge Bases,<br/>Guardrails]
        end

        Bedrock[🤖 AWS Bedrock<br/>Foundation Models<br/>Claude, Amazon Nova]
        Logs[📊 CloudWatch Logs<br/>/ecs/tac-bedrock-server]
    end

    Customer -->|1. Call/SMS| Phone
    Phone -->|2. Webhook POST| HTTPS
    HTTPS -->|3. HTTP Request<br/>/twiml or /webhook| ALB
    ALB -->|4. Forward to| ECS
    ECS -->|5. Create Conversation| Orchestrator
    ECS -->|6. Retrieve Profile| Memory
    ECS -->|7. Invoke Agent| Agent
    Agent -->|8. LLM Inference| Bedrock
    ECS -->|9. Write Logs| Logs
    ECS -->|10. WebSocket Audio<br/>or SMS Response| Phone
    Phone -->|11. Response| Customer

    style Customer fill:#e1f5ff
    style Twilio fill:#f0f0f0
    style HTTPS fill:#d4f1f4
    style AWS fill:#fff4e6
    style VPC fill:#e8f5e9
    style ECS fill:#fff9c4
    style BedrockAgent fill:#f3e5f5
    style Agent fill:#e1bee7
    style Bedrock fill:#f3e5f5
    style Logs fill:#e3f2fd
```

---

## AWS Services

### Core Services

| Service | Purpose |
|---------|---------|
| **AWS Bedrock Agent** | Fully managed agent with actions, knowledge bases, and guardrails |
| **ECS Fargate** | Container runtime for TAC server |
| **Application Load Balancer** | Stable DNS endpoint, health checks, WebSocket support |
| **AWS Bedrock** | LLM inference - Claude, Amazon Nova, etc. (pay-per-token) |
| **VPC** | Network isolation (10.0.0.0/16) |
| **Internet Gateway** | Internet connectivity |
| **Security Groups** | Firewall rules |
| **CloudWatch Logs** | Application logs (7-day retention) |
| **IAM Roles** | AWS permissions management (Bedrock access) |

### Optional Services (HTTPS Layer)

| Service | Purpose |
|---------|---------|
| **ngrok** | HTTPS tunnel for testing/development |
| **CloudFront** | HTTPS endpoint with free AWS domain |
| **Route53 + ACM** | Custom domain with AWS certificate |

---

## Deployment

### Prerequisites

- AWS CLI configured with appropriate credentials
- Python 3.10+ (Python 3.13 recommended)
- Docker installed
- AWS account with:
  - Bedrock Agent already deployed
  - IAM permissions for ECS, VPC, ALB
  - Region: us-east-1 (or your preferred region)
- HTTPS endpoint (choose one):
  - **ngrok** - For testing and development
  - **CloudFront** - For production with AWS-provided HTTPS domain
  - **Route53 + ACM** - For production with custom domain
- Twilio account with:
  - Account SID
  - Auth Token
  - API Key and Secret
  - Phone number
  - Conversation Configuration ID from Conversation Orchestrator

**Where to find Twilio credentials:**
- Account SID & Auth Token: Twilio Console → Account → API Keys & Tokens
- API Key & Secret: Twilio Console → Account → API Keys & Tokens
- Conversation Configuration ID: Twilio Console → Conversation Orchestrator → Configuration

**Where to find Bedrock Agent credentials:**
- Bedrock Agent ID: AWS Console → Bedrock → Agents → Select your agent
- Bedrock Agent Alias ID: AWS Console → Bedrock → Agents → Select your agent → Aliases (default: TSTALIASID)

### Step 0: Build and Publish Docker Image

**1. Build Docker image:**

```bash
# From the bedrock_aws_fargate directory
docker build -t tac-bedrock-server:latest .
```

**2. Publish to AWS ECR:**

Publish your Docker image to AWS ECR. You'll need the ECR image URI for Step 1.

Example URI format: `123456789012.dkr.ecr.us-east-1.amazonaws.com/tac-bedrock-server:latest`

### Step 1: Deploy CloudFormation Stack

Deploy the infrastructure (from the bedrock_aws_fargate directory):

```bash
aws cloudformation deploy \
  --template-file cloudformation.yaml \
  --stack-name TACBedrockStack \
  --parameter-overrides \
    ImageURI=YOUR_ECR_URI:latest \
    TwilioAccountSid=YOUR_ACCOUNT_SID \
    TwilioAuthToken=YOUR_AUTH_TOKEN \
    TwilioApiKey=YOUR_API_KEY \
    TwilioApiSecret=YOUR_API_SECRET \
    TwilioPhoneNumber=YOUR_PHONE_NUMBER \
    TwilioConversationConfigurationId=YOUR_CONVERSATION_CONFIGURATION_ID \
    TwilioVoicePublicDomain=YOUR_HTTPS_DOMAIN \
    BedrockAgentId=YOUR_BEDROCK_AGENT_ID \
    BedrockAgentAliasId=TSTALIASID \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

### Step 2: Get ALB DNS Name

```bash
aws cloudformation describe-stacks \
  --stack-name TACBedrockStack \
  --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' \
  --output text \
  --region us-east-1
```

**Output example:** `TAC-Bedrock-ALB-xxx.us-east-1.elb.amazonaws.com`

### Step 3: Connect HTTPS Endpoint to ALB

Point your HTTPS endpoint to the ALB DNS from Step 2.

For example, if using ngrok:
```bash
ngrok http TAC-Bedrock-ALB-xxx.us-east-1.elb.amazonaws.com:80 --domain=your-domain.ngrok.app
```

### Step 4: Configure Twilio Webhooks

**Voice (Phone Numbers):**
1. Go to Twilio Console → Phone Numbers → Active Numbers
2. Select your phone number
3. Set **Voice URL:** `https://your-https-domain.com/twiml` (POST)

**SMS (Conversation Orchestrator):**
1. Go to Twilio Console → Conversation Orchestrator
2. Select your Conversation Service
3. Configure webhook
4. Set **Webhook URL:** `https://your-https-domain.com/webhook` (POST)

### Step 5: Test Your Deployment

Make a phone call or send an SMS message to your Twilio phone number to test the deployment.
