"""WebSocket handling for AgentCore connector."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import TYPE_CHECKING, Any

from tac.channels.voice import VoiceChannel
from tac.core.logging import get_logger
from tac.models.session import ConversationSession

if TYPE_CHECKING:
    from websockets.client import WebSocketClientProtocol

logger = get_logger(__name__)


async def handle_websocket_message(
    websocket_factory: Callable[[ConversationSession], Awaitable[WebSocketClientProtocol]],
    websocket_payload_fn: Callable[[ConversationSession, str, str | None], dict[str, Any]],
    agent_connections: dict[str, WebSocketClientProtocol],
    context: ConversationSession,
    user_message: str,
    memory_context: str | None,
    voice_channel: VoiceChannel,
) -> None:
    """
    Handle voice message via WebSocket streaming (low-latency mode).

    Flow:
    1. Get or create WebSocket connection (pooled per session)
    2. Build payload via user's payload function
    3. Send payload to agent
    4. Stream response back to voice channel

    Args:
        websocket_factory: Function to create WebSocket connection
        websocket_payload_fn: Function to build WebSocket message payload
        agent_connections: Connection pool (session_id -> WebSocket)
        context: Conversation session with metadata
        user_message: The user's message text
        memory_context: Optional memory context string from TAC
        voice_channel: Voice channel instance
    """
    # Get or create WebSocket connection for this session
    agent_ws = await get_or_create_agent_ws(websocket_factory, agent_connections, context)

    # Build payload via user's payload function
    payload = websocket_payload_fn(context, user_message, memory_context)

    # Send payload to agent
    await agent_ws.send(json.dumps(payload))

    # Stream response to voice channel
    response_stream = stream_from_websocket(agent_ws)
    await voice_channel.send_response(context.conversation_id, response_stream, role="assistant")


async def get_or_create_agent_ws(
    websocket_factory: Callable[[ConversationSession], Awaitable[WebSocketClientProtocol]],
    agent_connections: dict[str, WebSocketClientProtocol],
    context: ConversationSession,
) -> WebSocketClientProtocol:
    """
    Get existing WebSocket connection or create new one.

    Implements connection pooling per session_id:
    - Returns existing connection if open
    - Creates new connection if none exists or connection closed
    - Stores connection in pool for reuse

    Args:
        websocket_factory: User-provided function to create WebSocket connection
        agent_connections: Connection pool (session_id -> WebSocket)
        context: Conversation session with metadata

    Returns:
        Open WebSocket connection to agent
    """
    session_id = context.conversation_id

    # Check if we have an existing open connection
    if session_id in agent_connections:
        ws = agent_connections[session_id]
        # Verify connection is still open
        if hasattr(ws, "state") and ws.state.name == "OPEN":
            logger.info(f"Reusing WebSocket connection for session {session_id}")
            return ws
        else:
            # Connection closed, remove from pool
            logger.info(f"WebSocket connection closed for session {session_id}, creating new one")
            del agent_connections[session_id]

    # Call user's factory to create new connection
    logger.info(f"Creating new WebSocket connection for session {session_id}")
    ws = await websocket_factory(context)
    agent_connections[session_id] = ws
    return ws


async def stream_from_websocket(agent_ws: WebSocketClientProtocol) -> AsyncGenerator[str, None]:
    """
    Stream text tokens from agent WebSocket.

    Parses WebSocket messages and yields text tokens for voice channel streaming.
    Supports message types: "text" (with tokens), "error" (with error message).

    Args:
        agent_ws: WebSocket connection to agent

    Yields:
        Text tokens from agent response
    """
    async for message in agent_ws:
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "text":
                token = data.get("token", "")
                is_last = data.get("last", False)

                # Yield token if not empty
                if token:
                    yield token

                # Stop if this is the last token
                if is_last:
                    break

            elif msg_type == "error":
                error_msg = data.get("message", "Unknown error from agent")
                logger.error(f"Agent error: {error_msg}")
                break

        except json.JSONDecodeError:
            logger.error("Invalid JSON from agent WebSocket", message=message)
            break


async def handle_conversation_ended(
    agent_connections: dict[str, WebSocketClientProtocol], context: ConversationSession
) -> None:
    """
    Clean up WebSocket connection when conversation ends.

    Args:
        agent_connections: Connection pool dict
        context: Conversation session with metadata
    """
    session_id = context.conversation_id
    if session_id in agent_connections:
        ws = agent_connections[session_id]
        try:
            await ws.close()
            logger.info(f"Closed WebSocket connection for session {session_id}")
        except Exception as e:
            logger.warning(
                f"Error closing WebSocket for session {session_id}: {e}",
                conversation_id=session_id,
            )
        finally:
            del agent_connections[session_id]


async def handle_interrupt(
    agent_connections: dict[str, WebSocketClientProtocol],
    context: ConversationSession,
    interrupt_data: dict[str, Any],
) -> None:
    """
    Forward interrupt to agent via WebSocket.

    Args:
        agent_connections: Connection pool dict
        context: Conversation session with metadata
        interrupt_data: Interrupt data from TAC (includes utterance_until_interrupt)
    """
    session_id = context.conversation_id
    if session_id not in agent_connections:
        logger.debug(f"No WebSocket connection to interrupt for session {session_id}")
        return

    ws = agent_connections[session_id]
    try:
        # Send interrupt message to agent
        # Extract utterance - handle both dict and Pydantic model
        utterance = ""
        if hasattr(interrupt_data, "utterance_until_interrupt"):
            utterance = interrupt_data.utterance_until_interrupt or ""
        elif isinstance(interrupt_data, dict):
            utterance = interrupt_data.get("utterance_until_interrupt", "")

        payload = {
            "type": "interrupt",
            "utterance_until_interrupt": utterance,
        }
        await ws.send(json.dumps(payload))
        logger.info(f"Sent interrupt to agent for session {session_id}")
    except Exception as e:
        logger.error(
            f"Error sending interrupt to agent: {e}",
            conversation_id=session_id,
            exc_info=True,
        )
