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
        return handle_voice_twiml(event)
    elif request_path.startswith('/webhook'):
        return handle_conversation_webhook(event)
    else:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Not found'})
        }


def handle_voice_twiml(event):
    """Handle voice call - generate TwiML.

    Uses CallSid as session_id for AgentCore routing to ensure the call is routed
    to a dedicated agent instance based on CallSid.
    """
    try:
        # Extract CallSid from Twilio webhook request
        call_sid = _extract_call_sid(event)
        if not call_sid:
            logger.warning("Missing CallSid in voice webhook request")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Missing CallSid parameter'})
            }

        # Generate presigned WebSocket URL with CallSid as session_id
        websocket_url = agentcore_runtime_client.generate_presigned_url(
            runtime_arn=AGENTCORE_RUNTIME_ARN,
            session_id=call_sid,
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


def _extract_call_sid(event):
    """Extract CallSid from Lambda event (POST body or query string)."""
    # Try POST body first (form-encoded)
    body = event.get('body', '')
    if body:
        from urllib.parse import parse_qs
        if event.get('isBase64Encoded'):
            import base64
            body = base64.b64decode(body).decode('utf-8')
        params = parse_qs(body)
        call_sid = params.get('CallSid', [None])[0]
        if call_sid:
            return call_sid

    # Fall back to query string parameters
    query_params = event.get('queryStringParameters') or {}
    return query_params.get('CallSid')


def handle_conversation_webhook(event):
    """Handle conversation webhook - forward to AgentCore.

    Conversation Orchestrator sends JSON webhooks. TAC processes only:
    - COMMUNICATION_CREATED: New message from customer (data.conversationId)
    - CONVERSATION_UPDATED: Conversation status changed (data.id)

    Other event types are ignored.
    """
    try:
        body = event.get('body', '')
        headers = event.get('headers', {})

        # Parse webhook to extract conversation_id for session routing
        webhook_data = json.loads(body)
        event_type = webhook_data.get('eventType')
        event_data = webhook_data.get('data', {})

        # Only process events that TAC handles
        if event_type not in ('COMMUNICATION_CREATED', 'CONVERSATION_UPDATED'):
            logger.debug(f"Ignoring event type: {event_type}")
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'success': True, 'ignored': True})
            }

        # Extract conversation_id based on event type
        conversation_id = None
        if event_type == 'COMMUNICATION_CREATED':
            # COMMUNICATION_CREATED: conversation_id at data.conversationId
            conversation_id = event_data.get('conversationId')
        elif event_type == 'CONVERSATION_UPDATED':
            # CONVERSATION_UPDATED: conversation_id at data.id
            conversation_id = event_data.get('id')

        if not conversation_id:
            logger.warning(f"Missing conversationId for event type {event_type}")
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Missing conversationId'})
            }

        payload = json.dumps({
            'webhook_data': body,
            'idempotency_token': headers.get('i-twilio-idempotency-token')
        }).encode()

        # Pass conversation_id as runtimeSessionId for sticky routing to same microVM
        agent_core_client.invoke_agent_runtime(
            agentRuntimeArn=AGENTCORE_RUNTIME_ARN,
            runtimeSessionId=conversation_id,
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
