"""
Twilio webhook signature validation for AWS Lambda.

Handles signature validation for both form-encoded and JSON webhooks.
"""

import base64
from urllib.parse import parse_qsl

from tac.core.logging import get_logger
from twilio.request_validator import RequestValidator

logger = get_logger(__name__)


class TwilioSignatureValidator:
    """Validates Twilio webhook signatures for AWS Lambda events."""

    def __init__(self, auth_token: str):
        """Initialize validator with Twilio auth token."""
        self.request_validator = RequestValidator(auth_token)

    def validate(self, event: dict) -> bool:
        """Validate Twilio webhook signature from Lambda event.

        Handles different content types:
        - Form-encoded: Parses body with blank values preserved
        - JSON with bodySHA256: Validates using body string
        - Other: Validates using body string

        Args:
            event: AWS Lambda event dict

        Returns:
            True if signature is valid, False otherwise
        """
        headers = event.get("headers", {})
        signature = headers.get("x-twilio-signature", "")

        if not signature:
            logger.warning("Missing X-Twilio-Signature header")
            return False

        url = self._construct_request_url(event, headers)
        body = self._decode_request_body(event)
        content_type = headers.get("content-type", "")

        # Determine validation data based on content type
        if "application/x-www-form-urlencoded" in content_type:
            # Form-encoded: parse body with blank values preserved
            validation_data = dict(parse_qsl(body, keep_blank_values=True))
        else:
            # JSON or other: use body string
            validation_data = body

        is_valid = self.request_validator.validate(url, validation_data, signature)

        if not is_valid:
            logger.warning(f"Invalid Twilio signature for URL: {url}")

        return is_valid

    @staticmethod
    def _construct_request_url(event: dict, headers: dict) -> str:
        """Construct full request URL from Lambda event."""
        domain = headers.get("host", "")
        path = event.get("rawPath", event.get("path", "/"))
        query_string = event.get("rawQueryString", "")

        url = f"https://{domain}{path}"
        if query_string:
            url = f"{url}?{query_string}"

        return url

    @staticmethod
    def _decode_request_body(event: dict) -> str:
        """Decode request body, handling base64 encoding if present."""
        body = event.get("body", "")
        is_base64 = event.get("isBase64Encoded", False)

        if is_base64 and body:
            body = base64.b64decode(body).decode("utf-8")

        return body
