"""AWS-specific server utilities for TAC.

Provides TACAWSFastAPIServer which wraps TACFastAPIServer with middleware
to handle AWS ALB + ngrok deployments where X-Forwarded headers need fixing.

Also provides AgentCore utilities for serverless deployment on AWS Bedrock AgentCore.
"""

__all__ = []

try:
    from tac_aws.server.fastapi_server import TACAWSFastAPIServer  # noqa: F401

    __all__.append("TACAWSFastAPIServer")
except ModuleNotFoundError as e:
    # Only catch missing tac[server] dependency (fastapi, uvicorn, etc.)
    # Re-raise if it's a bug in our code (e.g., wrong import path)
    if e.name not in ("fastapi", "uvicorn", "tac.server"):
        raise

try:
    from tac_aws.server.agentcore_app import (  # noqa: F401
        TACAgentCoreApp,
        TACAgentCoreWebSocketAdapter,
    )

    __all__.extend(["TACAgentCoreApp", "TACAgentCoreWebSocketAdapter"])
except ModuleNotFoundError as e:
    # Only catch missing bedrock_agentcore dependency
    # Re-raise if it's a bug in our code
    if e.name != "bedrock_agentcore":
        raise
