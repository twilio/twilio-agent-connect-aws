"""HTTP handling for AgentCore connector."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator, Callable
from typing import TYPE_CHECKING

from tac.channels.sms import SMSChannel
from tac.channels.voice import VoiceChannel
from tac.core.logging import get_logger
from tac.models.session import ConversationSession

if TYPE_CHECKING:
    from mypy_boto3_bedrock_agentcore.type_defs import InvokeAgentRuntimeResponseTypeDef

logger = get_logger(__name__)


async def parse_streaming_response(
    response: InvokeAgentRuntimeResponseTypeDef,
) -> AsyncGenerator[str, None]:
    """
    Parse streaming HTTP response from invoke_agent_runtime.

    Supports multiple content types:
    - text/event-stream: Real-time streaming (most common)
    - application/json: Buffered JSON chunks
    - Other: Raw content fallback

    Uses asyncio.to_thread() to run blocking boto3 reads in thread pool,
    preventing event loop blocking.

    Args:
        response: InvokeAgentRuntimeResponseTypeDef from boto3 client

    Yields:
        Text chunks from agent response
    """
    content_type = response.get("contentType", "")
    streaming_body = response.get("response")

    if not streaming_body:
        return

    # Handle text/event-stream (most common for streaming agents)
    if "text/event-stream" in content_type:
        if hasattr(streaming_body, "iter_lines"):

            def read_line() -> bytes | None:
                """Read a single line from the stream (blocking operation)."""
                try:
                    line: bytes = next(streaming_body.iter_lines(chunk_size=10))
                    return line
                except StopIteration:
                    return None

            while True:
                # Run blocking read in thread pool to avoid blocking event loop
                line = await asyncio.to_thread(read_line)
                if line is None:
                    break
                if line:
                    line_str = line.decode("utf-8") if isinstance(line, bytes) else line
                    # Parse "data: " prefixed lines (SSE format)
                    if line_str.startswith("data: "):
                        chunk_text = line_str[6:]  # Remove "data: " prefix
                        if chunk_text and chunk_text != "[DONE]":
                            # Try to parse as JSON (agent may return structured response)
                            try:
                                data = json.loads(chunk_text)
                                # Extract token from {"type": "text", "token": "..."}
                                if isinstance(data, dict) and data.get("type") == "text":
                                    token = data.get("token", "")
                                    if token:
                                        yield token
                                # Fallback: yield entire data if structure is different
                                elif isinstance(data, dict) and "text" in data:
                                    yield str(data["text"])
                                else:
                                    yield chunk_text
                            except json.JSONDecodeError:
                                # Not JSON, yield raw text (backward compatibility)
                                yield chunk_text

    # Handle application/json (buffered chunks)
    elif content_type == "application/json":

        def read_all_chunks() -> list[str]:
            """Read all chunks synchronously."""
            chunks = []
            for chunk in streaming_body:
                chunk_str = chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
                chunks.append(chunk_str)
            return chunks

        # Run blocking read in thread pool
        chunks = await asyncio.to_thread(read_all_chunks)
        full_content = "".join(chunks)

        try:
            data = json.loads(full_content)
            # Extract text and yield
            if isinstance(data, dict):
                text = data.get("text") or data.get("response") or str(data)
                yield str(text)
            else:
                yield str(data)
        except json.JSONDecodeError:
            yield full_content

    # Handle other content types
    else:

        def read_all() -> str:
            """Read all content synchronously."""
            if hasattr(streaming_body, "read"):
                content = streaming_body.read()
                return content.decode("utf-8") if isinstance(content, bytes) else content
            return ""

        # Run blocking read in thread pool
        content_str = await asyncio.to_thread(read_all)
        if content_str:
            yield content_str


async def handle_http_message(
    invoke_fn: Callable[[ConversationSession, str, str | None], InvokeAgentRuntimeResponseTypeDef],
    user_message: str,
    context: ConversationSession,
    memory_context: str | None,
    voice_channel: VoiceChannel,
    sms_channel: SMSChannel,
) -> None:
    """
    Handle message via HTTP invocation and route response.

    Flow:
    1. Call user's invoke function to get streaming response
    2. Parse streaming response into text chunks
    3. Route to channel:
       - Voice: Stream chunks immediately for low latency
       - SMS: Buffer complete response then send

    Args:
        invoke_fn: User-provided function to invoke agent
        user_message: The user's message text
        context: Conversation session with metadata
        memory_context: Optional memory context string from TAC
        voice_channel: Voice channel instance
        sms_channel: SMS channel instance
    """
    # Call user's invoke function to get response object
    response = invoke_fn(context, user_message, memory_context)

    # Parse streaming response
    response_stream = parse_streaming_response(response)

    # Route response based on channel
    if context.channel == "voice" and voice_channel:
        # Voice: stream response chunks immediately
        await voice_channel.send_response(
            context.conversation_id, response_stream, role="assistant"
        )
    elif context.channel == "sms" and sms_channel:
        # SMS: buffer complete response then send
        response_text = "".join([chunk async for chunk in response_stream])
        await sms_channel.send_response(context.conversation_id, response_text, role="assistant")
    else:
        logger.error(
            f"No channel handler for {context.channel}",
            conversation_id=context.conversation_id,
        )
