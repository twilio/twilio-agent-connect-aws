"""AWS integrations for Twilio Agent Connect (TAC).

This package provides AWS-specific connectors and server utilities for TAC:

Connectors:
    - StrandsConnector: AWS Strands SDK integration with multi-channel support
    - BedrockAgentCoreConnector: AWS Bedrock Agent Core integration with multi-channel support

Server:
    - TACAWSFastAPIServer: FastAPI server with AWS ALB header fixing for Twilio webhooks

Tools:
    - create_memory_tool: Strands tool for Twilio Memory retrieval
"""

from tac_aws._version import __version__

# Import connectors
from tac_aws.connectors import BedrockAgentCoreConnector, StrandsConnector

# Import server utilities (optional, requires tac[server])
try:
    from tac_aws.server import TACAWSFastAPIServer
    _has_server = True
except ImportError:
    _has_server = False
    TACAWSFastAPIServer = None  # type: ignore

__all__ = [
    "__version__",
    # Connectors
    "BedrockAgentCoreConnector",
    "StrandsConnector",
]

if _has_server:
    __all__.append("TACAWSFastAPIServer")
