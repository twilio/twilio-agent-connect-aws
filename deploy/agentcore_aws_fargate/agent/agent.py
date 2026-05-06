import json
import logging
from strands import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp

logger = logging.getLogger(__name__)

agent = Agent(
    model="us.amazon.nova-pro-v1:0",  # Use cross-region inference profile
    system_prompt=(
        "You are a helpful assistant. Respond naturally in plain text. "
        "IMPORTANT: Never use markdown formatting - no asterisks, no bold, no italics, no code blocks. "
        "Just respond with plain conversational text. "
        "Be helpful and provide complete, informative responses."
    )
)
app = BedrockAgentCoreApp()


@app.entrypoint
async def invoke(payload):
    """HTTP streaming entrypoint - yields tokens for streaming response"""
    user_message = payload.get("prompt", "Hello")
    logger.info(f"HTTP invocation with message: {user_message[:50]}...")

    # Stream response token by token
    async for chunk in agent.stream_async(user_message):
        # Strands stream_async returns dicts with 'data' key containing the text token
        if isinstance(chunk, dict) and 'data' in chunk:
            token = chunk['data']
            if token:
                yield {"type": "text", "token": token}


@app.websocket
async def websocket_handler(websocket, context):
    """WebSocket entrypoint - low-latency streaming for voice"""
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for session: {context.session_id}")

    try:
        while True:
            # Receive message from WebSocket
            data = await websocket.receive_text()
            message = json.loads(data)

            logger.info(f"WebSocket message type: {message.get('type')}")

            if message.get("type") == "prompt":
                user_message = message.get("voicePrompt", "")
                memory_context = message.get("memoryContext")

                # Prepend memory context if provided
                if memory_context:
                    user_message = f"{memory_context}\n\nUser: {user_message}"

                logger.info(f"Processing voice prompt: {user_message[:50]}...")

                # Stream tokens back via WebSocket
                try:
                    async for chunk in agent.stream_async(user_message):
                        # Strands stream_async returns dicts with 'data' key containing the text token
                        if isinstance(chunk, dict) and 'data' in chunk:
                            token = chunk['data']
                            if token:
                                response = {
                                    "type": "text",
                                    "token": token,
                                    "last": False
                                }
                                await websocket.send_text(json.dumps(response))

                    # Send final message
                    await websocket.send_text(json.dumps({
                        "type": "text",
                        "token": "",
                        "last": True
                    }))

                except Exception as e:
                    logger.error(f"Error streaming response: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": str(e)
                    }))

            elif message.get("type") == "interrupt":
                # Handle interruption - stop current generation
                logger.info("Interrupt received")
                # Agent should stop generating (implementation depends on agent capabilities)

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info(f"WebSocket connection closed for session: {context.session_id}")


if __name__ == "__main__":
    app.run()
