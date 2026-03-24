"""AWS integrations for Twilio Agent Connect (TAC).

This package provides AWS-specific adapters and handlers for TAC:

Adapters:
    - StrandsAdapter: AWS Strands SDK integration with per-conversation agents

Handlers:
    - OmniChannelHandler: Multi-channel message processing with adapter integration

Tools:
    - create_memory_tool: Strands tool for Twilio Memory retrieval
"""

__version__ = "0.1.0"

# Import adapters
from tac_aws.adapters import StrandsAdapter

# Import handlers
from tac_aws.handlers import OmniChannelHandler

__all__ = [
    "__version__",
    # Adapters
    "StrandsAdapter",
    # Handlers
    "OmniChannelHandler",
]
