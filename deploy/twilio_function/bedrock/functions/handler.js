/**
 * Twilio Function: Bedrock Agent over SMS + Voice (no TAC)
 *
 * Handles the Twilio Conversation Orchestrator webhook directly, invokes a
 * Bedrock Agent, and sends the reply back via the Conversations Actions API.
 * Also serves a classic (turn-based) voice handler using <Gather>/<Say> TwiML.
 *
 * SMS flow:
 *   1. Receive COMMUNICATION_CREATED webhook from Conversation Orchestrator
 *   2. Invoke the Bedrock Agent (sessionId = conversationId for continuity)
 *   3. POST a SEND_MESSAGE action to reply on the same conversation
 *
 * Voice flow (classic TwiML, request/response — no WebSocket):
 *   1. Call comes in → greet and open a <Gather input="speech">
 *   2. Caller speaks → Twilio re-POSTs with SpeechResult
 *   3. Invoke the Bedrock Agent (sessionId = CallSid for continuity), <Say> the
 *      reply, and <Gather> again to continue the conversation
 *
 * Endpoints:
 *   - /handler?route=webhook - SMS conversation webhook
 *   - /handler?route=voice   - Voice call webhook (returns TwiML)
 */

const {
  BedrockAgentRuntimeClient,
  InvokeAgentCommand,
} = require('@aws-sdk/client-bedrock-agent-runtime');

const bedrock = new BedrockAgentRuntimeClient({
  region: process.env.AWS_REGION || 'us-east-1',
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
  },
});

// When DEBUG is truthy, request the agent's reasoning/orchestration trace and
// log it. The trace is not persisted anywhere by Bedrock — it only comes back
// on the response stream — so we surface it via console.log for the Twilio
// Function live-tail (twilio serverless:logs --tail).
const DEBUG = /^(1|true|yes)$/i.test(process.env.DEBUG || '');

/**
 * Invoke the Bedrock Agent and collect the streamed completion into a string.
 */
async function invokeBedrockAgent(sessionId, inputText) {
  const response = await bedrock.send(
    new InvokeAgentCommand({
      agentId: process.env.BEDROCK_AGENT_ID,
      agentAliasId: process.env.BEDROCK_AGENT_ALIAS_ID || 'TSTALIASID',
      sessionId,
      inputText,
      enableTrace: DEBUG,
    })
  );

  let text = '';
  if (response.completion) {
    for await (const chunkEvent of response.completion) {
      const bytes = chunkEvent.chunk && chunkEvent.chunk.bytes;
      if (bytes) {
        text += Buffer.from(bytes).toString('utf-8');
      }
      if (DEBUG && chunkEvent.trace) {
        console.log(
          `[bedrock-trace ${sessionId}]`,
          JSON.stringify(chunkEvent.trace.trace)
        );
      }
    }
  }
  return text.trim();
}

/**
 * Send an SMS reply on a conversation via the Conversations Actions API.
 *
 * Uses address-based participant refs (from = our number, to = the customer),
 * so no participant lookup/reconciliation is needed. Auth is Basic with the
 * Twilio API key/secret.
 */
async function sendConversationReply(context, conversationId, toAddress, text) {
  const region = context.TWILIO_REGION;
  const base = region
    ? `https://conversations.${region}.twilio.com`
    : 'https://conversations.twilio.com';
  const url = `${base}/v2/Conversations/${conversationId}/Actions`;

  const auth = Buffer.from(
    `${context.TWILIO_API_KEY}:${context.TWILIO_API_SECRET}`
  ).toString('base64');

  const body = {
    type: 'SEND_MESSAGE',
    payload: {
      from: { channel: 'SMS', address: context.TWILIO_PHONE_NUMBER },
      to: [{ channel: 'SMS', address: toAddress }],
      content: { text },
    },
  };

  const res = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Basic ${auth}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new Error(`Conversations Actions API ${res.status}: ${detail}`);
  }
}

exports.handler = async function (context, event, callback) {
  if (event.route === 'voice') {
    return handleVoice(context, event, callback);
  }
  if (event.route === 'webhook') {
    return handleSms(context, event, callback);
  }

  console.warn(`[handler] 404 — unexpected route: ${event.route}`);
  const response = new Twilio.Response();
  response.appendHeader('Content-Type', 'application/json');
  response.setStatusCode(404);
  response.setBody({
    error: 'Route not found. Use /handler?route=webhook or /handler?route=voice',
  });
  return callback(null, response);
};

/**
 * SMS conversation webhook (Conversation Orchestrator → Bedrock → reply).
 */
async function handleSms(context, event, callback) {
  const response = new Twilio.Response();
  response.appendHeader('Content-Type', 'application/json');

  try {
    // Conversation Orchestrator sends JSON: { eventType, data: { ... } }.
    console.log(`[handler] webhook received — eventType=${event.eventType}`);

    // Only new inbound messages need a reply; ack everything else with 200.
    if (event.eventType !== 'COMMUNICATION_CREATED') {
      console.log(`[handler] ignoring non-message event: ${event.eventType}`);
      response.setStatusCode(200);
      response.setBody({ success: true, ignored: event.eventType });
      return callback(null, response);
    }

    const data = event.data || {};
    const conversationId = data.conversationId;
    const author = data.author || {};
    const authorAddress = author.address;
    const message = data.content && data.content.text ? data.content.text.trim() : '';

    console.log(
      `[handler] conversation=${conversationId} from=${authorAddress} message="${message}"`
    );

    // Ignore our own outbound messages (author is our agent number) and empties.
    if (!conversationId || !message || authorAddress === context.TWILIO_PHONE_NUMBER) {
      console.log(
        `[handler] skipping (empty, missing conversation, or own message from ${authorAddress})`
      );
      response.setStatusCode(200);
      response.setBody({ success: true, ignored: true });
      return callback(null, response);
    }

    console.log(`[handler] invoking Bedrock agent (session=${conversationId})...`);
    const started = Date.now();
    const reply =
      (await invokeBedrockAgent(conversationId, message)) ||
      'Sorry, I could not generate a response.';
    console.log(
      `[handler] Bedrock replied in ${Date.now() - started}ms: "${reply}"`
    );

    console.log(`[handler] sending reply to ${authorAddress} on ${conversationId}`);
    await sendConversationReply(context, conversationId, authorAddress, reply);
    console.log(`[handler] reply sent successfully`);

    response.setStatusCode(200);
    response.setBody({ success: true });
    return callback(null, response);
  } catch (error) {
    console.error('[handler] Error handling SMS webhook:', error);
    response.setStatusCode(500);
    response.setBody({ success: false, error: error.message });
    return callback(null, response);
  }
}

/**
 * Voice call webhook (classic TwiML, request/response — no WebSocket).
 *
 * Turn-based loop:
 *   - First hit (no SpeechResult): greet, then <Gather input="speech">.
 *   - Caller speaks: Twilio re-POSTs here with SpeechResult. We invoke the
 *     Bedrock Agent (sessionId = CallSid for continuity across turns), <Say>
 *     the reply, and <Gather> again to keep the conversation going.
 *   - Silence (gather times out): <Redirect> back here to re-open listening,
 *     so the line stays open until the caller hangs up.
 *
 * All turns POST back to this same endpoint (?route=voice), so the <Gather>
 * action points at the current request URL.
 */
async function handleVoice(context, event, callback) {
  const callSid = event.CallSid;
  const speech = (event.SpeechResult || '').trim();
  console.log(
    `[handler] voice — CallSid=${callSid} from=${event.From} speech="${speech}"`
  );

  const twiml = new Twilio.twiml.VoiceResponse();

  // Absolute action URL so <Gather> posts back to this exact endpoint. Falls
  // back to a relative path if DOMAIN_NAME isn't set (e.g. local dev).
  const actionUrl = context.DOMAIN_NAME
    ? `https://${context.DOMAIN_NAME}/handler?route=voice`
    : '/handler?route=voice';

  // Decide what to say this turn: greeting on first hit, agent reply on speech,
  // nothing on a silent re-listen loop (event.looped set by our own <Redirect>).
  let prompt = '';
  try {
    if (speech) {
      // Caller said something → get the agent's reply (session = CallSid).
      console.log(`[handler] invoking Bedrock agent (session=${callSid})...`);
      const started = Date.now();
      prompt =
        (await invokeBedrockAgent(callSid, speech)) ||
        'Sorry, I could not generate a response.';
      console.log(
        `[handler] Bedrock replied in ${Date.now() - started}ms: "${prompt}"`
      );
    } else if (!event.looped) {
      // First hit of the call → greet. (Silent re-listen loops carry looped=1.)
      prompt = 'Hello! Thanks for calling. How can I help you today?';
    }
  } catch (error) {
    console.error('[handler] Error handling voice turn:', error);
    twiml.say('Sorry, something went wrong. Goodbye.');
    twiml.hangup();
    return sendTwiml(callback, twiml);
  }

  // Nest the prompt INSIDE <Gather> so Twilio listens right after speaking it.
  // On speech, Twilio POSTs SpeechResult back to actionUrl (next turn).
  const gather = twiml.gather({
    input: 'speech',
    speechTimeout: 'auto',
    action: actionUrl,
    method: 'POST',
  });
  if (prompt) {
    gather.say(prompt);
  }

  // Silence: the gather timed out with no speech. Redirect back to re-open
  // listening (looped=1 suppresses the greeting) so the line stays open until
  // the caller hangs up.
  twiml.redirect({ method: 'POST' }, `${actionUrl}&looped=1`);

  return sendTwiml(callback, twiml);
}

/**
 * Serialize a VoiceResponse as TwiML and return it via the callback.
 */
function sendTwiml(callback, twiml) {
  const response = new Twilio.Response();
  response.appendHeader('Content-Type', 'application/xml');
  response.setBody(twiml.toString());
  return callback(null, response);
}
