"""AWS-specific server utilities for TAC.

Provides TACAWSFastAPIServer which wraps TACFastAPIServer with middleware
to handle AWS ALB + ngrok deployments where X-Forwarded headers need fixing.
"""

from tac_aws.server.fastapi_server import TACAWSFastAPIServer

__all__ = ["TACAWSFastAPIServer"]
