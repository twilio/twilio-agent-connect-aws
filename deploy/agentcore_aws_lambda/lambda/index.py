"""
Lambda Function - Twilio Webhook Proxy with TAC Integration

Endpoints:
- /twiml: Voice calls (generates TwiML using TAC)
- /webhook: Conversation webhooks (forwards to AgentCore)
"""

import json
import os

import boto3
from bedrock_agentcore.runtime import AgentCoreRuntimeClient
from tac.channels.voice.twiml import generate_twiml
from tac.core.logging import get_logger

from validation import TwilioSignatureValidator

logger = get_logger(__name__)

# Environment variables
AGENTCORE_RUNTIME_ARN = os.environ['AGENTCORE_RUNTIME_ARN']
TWILIO_CONVERSATION_CONFIGURATION_ID = os.environ['TWILIO_CONVERSATION_CONFIGURATION_ID']
TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']
AWS_REGION = os.environ['AWS_REGION']

# Initialize clients
agent_core_client = boto3.client('bedrock-agentcore')
agentcore_runtime_client = AgentCoreRuntimeClient(region=AWS_REGION)
signature_validator = TwilioSignatureValidator(TWILIO_AUTH_TOKEN)


def lambda_handler(event, context):
    """Route requests to appropriate handler."""
    # Validate Twilio signature
    if not signature_validator.validate(event):
        return {
            'statusCode': 403,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Invalid webhook signature'})
        }

    request_path = event.get('rawPath', event.get('path', '/'))

    if request_path.startswith('/twiml'):
        return handle_voice_twiml()
    elif request_path.startswith('/webhook'):
        return handle_conversation_webhook(event)
    else:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Not found'})
        }


def handle_voice_twiml():
    """Handle voice call - generate TwiML."""
    try:
        websocket_url = agentcore_runtime_client.generate_presigned_url(
            runtime_arn=AGENTCORE_RUNTIME_ARN,
            expires=300
        )

        twiml = generate_twiml(
            options={
                "websocket_url": websocket_url,
                "conversation_configuration": TWILIO_CONVERSATION_CONFIGURATION_ID
            }
        )

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/xml'},
            'body': twiml
        }

    except Exception as e:
        logger.error(f"Error generating TwiML: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }


def handle_conversation_webhook(event):
    """Handle conversation webhook - forward to AgentCore.

    Conversation Orchestrator sends JSON webhooks.
    """
    try:
        body = event.get('body', '')
        headers = event.get('headers', {})

        payload = json.dumps({
            'webhook_data': body,
            'idempotency_token': headers.get('i-twilio-idempotency-token')
        }).encode()

        agent_core_client.invoke_agent_runtime(
            agentRuntimeArn=AGENTCORE_RUNTIME_ARN,
            payload=payload
        )

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'success': True})
        }

    except Exception as e:
        logger.error(f"Error forwarding webhook to AgentCore: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }
