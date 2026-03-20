"""AWS-specific servers for TAC multi-channel support."""

from tac_aws.handlers import OmniChannelHandlers

try:
    from tac_aws.servers.fastapi import OmniChannelFastAPIServer
except ImportError:
    pass  # FastAPI not installed

__all__ = [
    "OmniChannelFastAPIServer",
    "OmniChannelHandlers",
]
