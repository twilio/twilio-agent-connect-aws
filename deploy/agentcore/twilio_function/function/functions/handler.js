/**
 * Twilio Function: Unified Handler for AgentCore Integration
 *
 * Endpoints:
 *   - /handler?route=twiml   - Voice call TwiML generation
 *   - /handler?route=webhook - SMS conversation webhook forwarding
 */

const {
  BedrockAgentCoreClient,
  InvokeAgentRuntimeCommand
} = require('@aws-sdk/client-bedrock-agentcore');

/**
 * Helper: Get AWS credentials from context
 */
function getAwsCredentials(context) {
  return {
    accessKeyId: context.AWS_ACCESS_KEY_ID,
    secretAccessKey: context.AWS_SECRET_ACCESS_KEY,
  };
}

exports.handler = async function(context, event, callback) {
  const route = event.route;

  if (route === 'twiml') {
    return handleVoiceTwiml(context, event, callback);
  } else if (route === 'webhook') {
    return handleConversationWebhook(context, event, callback);
  } else {
    const response = new Twilio.Response();
    response.setStatusCode(404);
    response.appendHeader('Content-Type', 'application/json');
    response.setBody({ error: 'Route not found. Use /handler?route=twiml or /handler?route=webhook' });
    return callback(null, response);
  }
};

/**
 * Generate pre-signed WebSocket URL for AgentCore using official client
 */
async function generatePresignedUrl(runtimeArn, region, credentials) {
  const { RuntimeClient } = await import('bedrock-agentcore/runtime');

  const client = new RuntimeClient({
    region: region,
    credentialsProvider: async () => credentials
  });

  const websocketUrl = await client.generatePresignedUrl({
    runtimeArn: runtimeArn,
    expires: 300
  });

  return websocketUrl;
}

/**
 * Handle Voice Call - Generate TwiML with WebSocket URL
 *
 * TODO: Add Twilio signature validation to prevent unauthorized access
 */
async function handleVoiceTwiml(context, event, callback) {
  try {
    console.log('Generating TwiML for voice call');

    const credentials = getAwsCredentials(context);

    // Generate pre-signed WebSocket URL
    const websocketUrl = await generatePresignedUrl(
      context.AGENTCORE_RUNTIME_ARN,
      context.AWS_REGION || 'us-east-1',
      credentials
    );

    // Generate TwiML with ConversationRelay
    // Note: conversationConfiguration must come BEFORE url (attribute order matters)
    const escapedUrl = websocketUrl.replace(/&/g, '&amp;');
    const twimlString = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <ConversationRelay conversationConfiguration="${context.TWILIO_CONVERSATION_CONFIGURATION_ID}" url="${escapedUrl}" />
  </Connect>
</Response>`;

    console.log('TwiML generated successfully');

    // Return TwiML directly via callback (don't use Twilio.Response for XML)
    callback(null, twimlString);

  } catch (error) {
    console.error('Error generating TwiML:', error);

    // Return error TwiML
    const errorTwiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>We are experiencing technical difficulties. Please try again later.</Say>
  <Hangup/>
</Response>`;

    callback(null, errorTwiml);
  }
}

/**
 * Handle SMS Conversation Webhook - Forward to AgentCore
 *
 * TODO: Add Twilio signature validation to prevent unauthorized access
 */
async function handleConversationWebhook(context, event, callback) {
  const response = new Twilio.Response();
  response.appendHeader('Content-Type', 'application/json');

  try {
    console.log('Processing conversation webhook');

    const credentials = getAwsCredentials(context);

    const client = new BedrockAgentCoreClient({
      region: context.AWS_REGION || 'us-east-1',
      credentials: credentials
    });

    const payload = {
      webhook_data: JSON.stringify(event),
      idempotency_token: event['I-Twilio-Idempotency-Token'] || event.MessageSid,
    };

    const command = new InvokeAgentRuntimeCommand({
      agentRuntimeArn: context.AGENTCORE_RUNTIME_ARN,
      payload: Buffer.from(JSON.stringify(payload)),
    });

    await client.send(command);

    console.log('AgentCore invocation successful');

    response.setStatusCode(200);
    response.setBody({
      success: true,
      message: 'Webhook forwarded to AgentCore',
    });

    return callback(null, response);

  } catch (error) {
    console.error('Error forwarding webhook to AgentCore:', error);

    response.setStatusCode(500);
    response.setBody({
      success: false,
      error: error.message,
    });

    return callback(null, response);
  }
}
