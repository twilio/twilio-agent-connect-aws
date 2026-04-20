"""Configuration schemas for AgentCore connector."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from mypy_boto3_bedrock_agentcore.type_defs import InvokeAgentRuntimeResponseTypeDef
    from tac.models.session import ConversationSession
    from websockets.client import WebSocketClientProtocol


class WebSocketConfig(BaseModel):
    """WebSocket configuration for voice channel optimization."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    factory: Callable[[ConversationSession], Awaitable[WebSocketClientProtocol]] = Field(
        ...,
        description="Async function to create WebSocket connection (called once per session for pooling)",
    )
    payload_fn: Callable[[ConversationSession, str, str | None], dict[str, Any]] = Field(
        ...,
        description="Function to build WebSocket message payload (called every message)",
    )


class RuntimeConfig(BaseModel):
    """Runtime configuration for AgentCore connector."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    http: Callable[[ConversationSession, str, str | None], InvokeAgentRuntimeResponseTypeDef] = (
        Field(
            ...,
            description="Function to invoke agent via HTTP (required for both channels)",
        )
    )
    websocket: WebSocketConfig | None = Field(
        None,
        description="Optional WebSocket configuration for voice channel optimization",
    )

    @field_validator("websocket", mode="before")
    @classmethod
    def validate_websocket(
        cls, v: dict[str, Any] | WebSocketConfig | None
    ) -> WebSocketConfig | None:
        """Convert dict to WebSocketConfig if needed."""
        if v is None:
            return None
        if isinstance(v, dict):
            return WebSocketConfig(**v)
        if isinstance(v, WebSocketConfig):
            return v
        return None


# Rebuild models to resolve forward references
try:
    from mypy_boto3_bedrock_agentcore.type_defs import InvokeAgentRuntimeResponseTypeDef
    from tac.models.session import ConversationSession
    from websockets.client import WebSocketClientProtocol

    WebSocketConfig.model_rebuild()
    RuntimeConfig.model_rebuild()
except ImportError:
    # Types not available at import time (e.g., during testing)
    pass
