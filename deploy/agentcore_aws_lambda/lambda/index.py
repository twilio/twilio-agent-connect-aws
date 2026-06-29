"""
Lambda Function - Twilio Webhook Proxy with TAC Integration

Endpoints:
- /twiml: Voice calls (generates TwiML using TAC)
- /webhook: Conversation webhooks (forwards to AgentCore)
"""

import os

from credentials import fetch_twilio_auth_token
from proxy import AgentCoreLambdaProxy

# Environment variables
AGENTCORE_RUNTIME_ARN = os.environ["AGENTCORE_RUNTIME_ARN"]
TWILIO_SECRET_ARN = os.environ["TWILIO_SECRET_ARN"]
TWILIO_CONVERSATION_CONFIGURATION_ID = os.environ["TWILIO_CONVERSATION_CONFIGURATION_ID"]

# Fetch Twilio auth token from Secrets Manager
twilio_auth_token = fetch_twilio_auth_token(TWILIO_SECRET_ARN)

proxy = AgentCoreLambdaProxy(
    agentcore_runtime_arn=AGENTCORE_RUNTIME_ARN,
    conversation_configuration_id=TWILIO_CONVERSATION_CONFIGURATION_ID,
    twilio_auth_token=twilio_auth_token,
)

# Expose lambda_handler for AWS Lambda runtime
lambda_handler = proxy.lambda_handler
