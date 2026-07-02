"""AWS-specific FastAPI server wrapper for TAC.

This module provides TACAWSFastAPIServer which extends TACFastAPIServer with
middleware to handle AWS ALB deployments. AWS ALB does not set X-Forwarded-Host
header, which causes Twilio signature validation to fail when using ngrok for testing.

Usage:
    from tac import TAC
    from tac.core.config import TACConfig
    from tac_aws.server import TACAWSFastAPIServer

    tac = TAC(config=TACConfig.from_env())

    # ... setup connectors ...

    server = TACAWSFastAPIServer(
        tac=tac,
        voice_channel=connector.voice,
        messaging_channels=[connector.sms],
        public_domain=os.getenv("TWILIO_VOICE_PUBLIC_DOMAIN")  # e.g., "myapp.ngrok.app"
    )

    if __name__ == "__main__":
        server.start()
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from tac.server import TACFastAPIServer, TACServerConfig

from tac_aws.server.middleware import ALBForwardedHeadersMiddleware

if TYPE_CHECKING:
    from fastapi import FastAPI
    from tac import TAC
    from tac.channels.messaging import MessagingChannel
    from tac.channels.voice import VoiceChannel

logger = logging.getLogger(__name__)


class TACAWSFastAPIServer(TACFastAPIServer):
    """AWS-specific FastAPI server for TAC with proxy header handling.

    This extends TACFastAPIServer by adding middleware to ensure X-Forwarded-Host
    and X-Forwarded-Proto headers are set correctly for Twilio signature validation.

    Required for AWS ALB deployments where ALB doesn't set X-Forwarded-Host, but
    also safe to use for local development with ngrok.

    The public_domain is automatically obtained from TACServerConfig.public_domain,
    which reads from TWILIO_VOICE_PUBLIC_DOMAIN environment variable.

    Example:
        from tac.server import TACServerConfig

        # Set TWILIO_VOICE_PUBLIC_DOMAIN=your-app.ngrok.app
        server = TACAWSFastAPIServer(
            tac=tac,
            voice_channel=voice,
            messaging_channels=[sms],
            config=TACServerConfig.from_env()
        )
        server.start()
    """

    def __init__(
        self,
        tac: TAC,
        voice_channel: VoiceChannel | None = None,
        messaging_channels: list[MessagingChannel] | None = None,
        config: TACServerConfig | None = None,
        app: FastAPI | None = None,
    ):
        """Initialize the AWS FastAPI server.

        Args:
            tac: The TAC instance.
            voice_channel: Optional voice channel (WebSocket).
            messaging_channels: Optional list of messaging channels (SMS, WhatsApp, etc).
            config: Optional TACServerConfig (if None, creates default config from env).
            app: Optional existing FastAPI app to wrap.
        """
        # Create config from env if not provided
        if config is None:
            config = TACServerConfig.from_env()

        super().__init__(tac, voice_channel, messaging_channels, config, app)

        # Get public domain from server config
        public_domain = config.public_domain if config.public_domain else None

        # Validate that public_domain is set for AWS ALB deployments
        if not public_domain:
            raise ValueError(
                "TACAWSFastAPIServer requires public_domain to be set. "
                "Set TWILIO_VOICE_PUBLIC_DOMAIN environment variable or pass "
                "config=TACServerConfig(public_domain='your-domain.ngrok.app'). "
                "If you don't need AWS ALB header fixing, use TACFastAPIServer instead."
            )

        # Add the ALB header middleware
        self.app.add_middleware(ALBForwardedHeadersMiddleware, public_domain=public_domain)
        logger.info(f"Added ALBForwardedHeadersMiddleware for domain: {public_domain}")
