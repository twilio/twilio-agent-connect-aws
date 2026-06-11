"""
Lambda Function - Twilio Webhook Proxy with TAC Integration

Endpoints:
- /twiml: Voice calls (generates TwiML using TAC)
- /webhook: Conversation webhooks (forwards to AgentCore)

This example shows using AWS Secrets Manager with TACAgentCoreLambdaProxy.
"""

import json
import os

import boto3

from lambda_proxy import TACAgentCoreLambdaProxy

# Environment variables
AGENTCORE_RUNTIME_ARN = os.environ['AGENTCORE_RUNTIME_ARN']
TWILIO_SECRET_ARN = os.environ['TWILIO_SECRET_ARN']

# Initialize secrets client
secrets_client = boto3.client('secretsmanager')

# Lazy-load secrets (cached after first invocation)
_secrets_cache = None


def _get_secrets():
    """Fetch secrets from Secrets Manager (cached after first call)."""
    global _secrets_cache
    if _secrets_cache is None:
        response = secrets_client.get_secret_value(SecretId=TWILIO_SECRET_ARN)
        _secrets_cache = json.loads(response['SecretString'])
    return _secrets_cache


# Initialize proxy with secrets from Secrets Manager
secrets = _get_secrets()
proxy = TACAgentCoreLambdaProxy(
    agentcore_runtime_arn=AGENTCORE_RUNTIME_ARN,
    twilio_auth_token=secrets['TWILIO_AUTH_TOKEN'],
    conversation_configuration_id=secrets['TWILIO_CONVERSATION_CONFIGURATION_ID']
)

# Lambda handler
lambda_handler = proxy.lambda_handler
