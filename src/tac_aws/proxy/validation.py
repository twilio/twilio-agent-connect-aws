"""
Twilio webhook signature validation for AWS Lambda.

Handles signature validation for both form-encoded and JSON webhooks.
"""

import base64
import binascii
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl

from tac.core.logging import get_logger

if TYPE_CHECKING:
    from twilio.request_validator import RequestValidator
else:
    try:
        from twilio.request_validator import RequestValidator
    except ImportError:
        RequestValidator = None  # type: ignore

logger = get_logger(__name__)


class TwilioSignatureValidator:
    """Validates Twilio webhook signatures for AWS Lambda events."""

    def __init__(self, auth_token: str) -> None:
        """Initialize validator with Twilio auth token.

        Raises:
            ImportError: If twilio package is not installed
        """
        if RequestValidator is None:
            raise ImportError(
                "twilio package is required for TwilioSignatureValidator. "
                "Install with: pip install twilio-agent-connect-aws[agentcore]"
            )
        self.request_validator = RequestValidator(auth_token)

    def validate(self, event: dict[str, Any]) -> bool:
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
        # Normalize headers to lowercase for case-insensitive lookup
        # Handle None headers dict and None header values
        raw_headers = event.get("headers") or {}
        headers = {k.lower(): (v or "") for k, v in raw_headers.items()}
        signature = headers.get("x-twilio-signature", "")

        if not signature:
            logger.warning("Missing X-Twilio-Signature header")
            return False

        url = self._construct_request_url(event, headers)
        body = self._decode_request_body(event)
        content_type = headers.get("content-type", "").lower()

        # Determine validation data based on content type
        validation_data: dict[str, str] | str
        if "application/x-www-form-urlencoded" in content_type:
            # Form-encoded: parse body with blank values preserved
            validation_data = dict(parse_qsl(body, keep_blank_values=True))
        else:
            # JSON or other: use body string
            validation_data = body

        is_valid: bool = bool(self.request_validator.validate(url, validation_data, signature))

        if not is_valid:
            logger.warning(f"Invalid Twilio signature for URL: {url}")

        return is_valid

    @staticmethod
    def _construct_request_url(event: dict[str, Any], headers: dict[str, str]) -> str:
        """Construct full request URL from Lambda Function URL event.

        Lambda Function URLs use the format:
        - rawPath: request path
        - rawQueryString: query string (already URL-encoded)
        - headers.host: domain
        """
        scheme = "https"
        domain = headers.get("host", "")
        path = event.get("rawPath", "/")
        query_string = event.get("rawQueryString", "")

        url = f"{scheme}://{domain}{path}"
        if query_string:
            url = f"{url}?{query_string}"

        return url

    @staticmethod
    def _decode_request_body(event: dict[str, Any]) -> str:
        """Decode request body, handling base64 encoding if present.

        Returns empty string if decoding fails (invalid base64 or non-UTF8).
        """
        body: str = event.get("body", "") or ""
        is_base64 = event.get("isBase64Encoded", False)

        if is_base64 and body:
            try:
                body = base64.b64decode(body).decode("utf-8")
            except (TypeError, binascii.Error, UnicodeDecodeError) as e:
                logger.warning(f"Failed to decode request body: {e}")
                return ""

        return body
