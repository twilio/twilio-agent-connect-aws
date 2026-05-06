"""ASGI middleware for AWS deployments."""

from __future__ import annotations

import logging

from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


class ALBForwardedHeadersMiddleware:
    """ASGI middleware to inject X-Forwarded headers for AWS ALB deployments.

    AWS ALB does not set X-Forwarded-Host header, and ngrok sets X-Forwarded-Proto
    to 'http' when forwarding to ALB on port 80. This middleware fixes both issues
    to ensure Twilio signature validation works correctly.

    This middleware works for both HTTP and WebSocket connections.
    """

    def __init__(self, app: ASGIApp, public_domain: str | None):
        """Initialize the middleware.

        Args:
            app: The ASGI application to wrap.
            public_domain: The public domain name (e.g., "myapp.ngrok.app").
                          If None, no header modifications are made.
        """
        self.app = app
        self.public_domain = public_domain

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process the request and inject X-Forwarded headers if needed."""
        if scope["type"] in ("http", "websocket") and self.public_domain:
            headers = list(scope.get("headers", []))

            # Check if X-Forwarded-Host exists
            has_forwarded_host = any(k.lower() == b"x-forwarded-host" for k, _ in headers)

            if not has_forwarded_host:
                # Add X-Forwarded-Host
                headers.append((b"x-forwarded-host", self.public_domain.encode()))
                logger.debug(f"Added X-Forwarded-Host: {self.public_domain}")

            # Force X-Forwarded-Proto to https for public domain
            # This is needed because ngrok forwards to ALB via http, but Twilio signs with https
            host_value = next(
                (v.decode() for k, v in headers if k.lower() == b"x-forwarded-host"), ""
            )
            if host_value == self.public_domain:
                # Remove existing X-Forwarded-Proto and add https
                headers = [(k, v) for k, v in headers if k.lower() != b"x-forwarded-proto"]
                headers.append((b"x-forwarded-proto", b"https"))
                logger.debug("Forced X-Forwarded-Proto to https")

            scope["headers"] = headers

        await self.app(scope, receive, send)
