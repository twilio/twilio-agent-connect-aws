"""Connectors for AWS agent integrations with TAC.

Connectors combine agent runtime integration with channel management
and conversation handling.
"""

from tac_aws.connectors.bedrock_agentcore_connector import BedrockAgentCoreConnector
from tac_aws.connectors.strands_connector import StrandsConnector

__all__ = [
    "BedrockAgentCoreConnector",
    "StrandsConnector",
]
