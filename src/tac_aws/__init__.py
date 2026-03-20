"""AWS integrations for Twilio Agent Connect (TAC).

This package provides AWS-specific adapters and servers for TAC:

Adapters:
    - StrandsAdapter: AWS Strands SDK integration
    - BedrockAdapter: AWS Bedrock Agent Runtime integration
    - BedrockAgentCoreAdapter: AWS Bedrock AgentCore integration

Servers:
    - OmniChannelFastAPIServer: FastAPI-based multi-channel server
    - OmniChannelAgentCoreServer: BedrockAgentCore-based multi-channel server

Handlers:
    - OmniChannelHandlers: Container for channel handler instances
"""

__version__ = "0.1.0"

# Import adapters
from tac_aws.adapters import (
    BedrockAdapter,
    BedrockAgentCoreAdapter,
    StrandsAdapter,
)

# Import handlers
from tac_aws.handlers import OmniChannelHandlers

# Import servers (only if dependencies are available)
try:
    from tac_aws.servers import (
        OmniChannelFastAPIServer,
    )
except ImportError:
    pass  # FastAPI not installed

try:
    from tac_aws.servers import (
        OmniChannelAgentCoreServer,
    )
except ImportError:
    pass  # BedrockAgentCore not installed

__all__ = [
    "__version__",
    # Adapters
    "StrandsAdapter",
    "BedrockAdapter",
    "BedrockAgentCoreAdapter",
    # Handlers
    "OmniChannelHandlers",
    # Servers
    "OmniChannelFastAPIServer",
    "OmniChannelAgentCoreServer",
]
