"""AWS integrations for Twilio Agent Connect (TAC).

This package provides AWS-specific connectors for TAC:

Connectors:
    - StrandsConnector: AWS Strands SDK integration with multi-channel support
    - BedrockAgentCoreConnector: AWS Bedrock Agent Core integration with multi-channel support

Tools:
    - create_memory_tool: Strands tool for Twilio Memory retrieval
"""

__version__ = "0.1.0"

# Import connectors
from tac_aws.connectors import BedrockAgentCoreConnector, StrandsConnector

__all__ = [
    "__version__",
    # Connectors
    "BedrockAgentCoreConnector",
    "StrandsConnector",
]
