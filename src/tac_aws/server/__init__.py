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
    # Only catch missing server dependencies (fastapi, uvicorn, starlette, tac[server], etc.)
    # Re-raise if it's a bug in our code (internal tac_aws import path error)
    if e.name is not None and e.name.startswith("tac_aws."):
        raise

try:
    from tac_aws.server.agentcore_app import (  # noqa: F401
        TACAgentCoreApp,
        TACAgentCoreWebSocketAdapter,
    )

    __all__.extend(["TACAgentCoreApp", "TACAgentCoreWebSocketAdapter"])
except ModuleNotFoundError as e:
    # Only catch missing agentcore dependencies (bedrock_agentcore, etc.)
    # Re-raise if it's a bug in our code (internal tac_aws import path error)
    if e.name is not None and e.name.startswith("tac_aws."):
        raise
