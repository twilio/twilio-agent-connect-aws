"""Tests for TwilioSignatureValidator."""

import base64
from unittest.mock import Mock, patch

import pytest

from tac_aws.proxy.validation import TwilioSignatureValidator

# Check if twilio is available
try:
    from twilio.request_validator import RequestValidator  # noqa: F401

    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

# Skip all tests if twilio is not installed (optional dependency)
pytestmark = pytest.mark.skipif(
    not TWILIO_AVAILABLE,
    reason="twilio package not installed (optional dependency)",
)


class TestTwilioSignatureValidator:
    """Test TwilioSignatureValidator functionality."""

    def test_initialization_without_twilio_raises_error(self):
        """Test that initialization fails gracefully when twilio is not installed."""
        with patch("tac_aws.proxy.validation.RequestValidator", None):
            with pytest.raises(
                ImportError,
                match="twilio package is required for TwilioSignatureValidator",
            ):
                TwilioSignatureValidator("test_token")

    def test_initialization_with_auth_token(self):
        """Test validator initializes with auth token."""
        validator = TwilioSignatureValidator("test_auth_token")
        assert validator.request_validator is not None

    def test_validate_missing_signature(self):
        """Test validation fails when X-Twilio-Signature is missing."""
        validator = TwilioSignatureValidator("test_token")
        event = {"headers": {}, "body": ""}

        assert validator.validate(event) is False

    def test_validate_case_insensitive_headers(self):
        """Test that header lookup is case-insensitive."""
        validator = TwilioSignatureValidator("test_token")

        # Mock request_validator.validate to return True
        validator.request_validator.validate = Mock(return_value=True)

        # Headers with mixed casing
        event = {
            "headers": {
                "X-Twilio-Signature": "test_sig",
                "Host": "example.com",
                "Content-Type": "application/json",
            },
            "rawPath": "/webhook",
            "body": "{}",
        }

        result = validator.validate(event)
        assert result is True

    def test_construct_url_function_url_format(self):
        """Test URL construction for Lambda Function URL."""
        event = {
            "rawPath": "/webhook",
            "rawQueryString": "param1=value1&param2=value2",
        }
        headers = {"host": "lambda-url.us-east-1.on.aws"}

        url = TwilioSignatureValidator._construct_request_url(event, headers)
        assert url == "https://lambda-url.us-east-1.on.aws/webhook?param1=value1&param2=value2"

    def test_construct_url_with_query_params(self):
        """Test URL construction with query parameters."""
        event = {
            "rawPath": "/webhook",
            "rawQueryString": "param1=value1&param2=value2",
        }
        headers = {"host": "api.example.com"}

        url = TwilioSignatureValidator._construct_request_url(event, headers)
        assert url == "https://api.example.com/webhook?param1=value1&param2=value2"

    def test_construct_url_no_query_string(self):
        """Test URL construction without query string."""
        event = {"rawPath": "/webhook"}
        headers = {"host": "example.com"}

        url = TwilioSignatureValidator._construct_request_url(event, headers)
        assert url == "https://example.com/webhook"

    def test_decode_request_body_plain_text(self):
        """Test decoding plain text body."""
        event = {"body": "test body", "isBase64Encoded": False}

        body = TwilioSignatureValidator._decode_request_body(event)
        assert body == "test body"

    def test_decode_request_body_base64(self):
        """Test decoding base64-encoded body."""
        original = "test body"
        encoded = base64.b64encode(original.encode("utf-8")).decode("utf-8")
        event = {"body": encoded, "isBase64Encoded": True}

        body = TwilioSignatureValidator._decode_request_body(event)
        assert body == original

    def test_decode_request_body_invalid_base64(self):
        """Test that invalid base64 returns empty string and logs warning."""
        event = {"body": "not-valid-base64!!!", "isBase64Encoded": True}

        body = TwilioSignatureValidator._decode_request_body(event)
        assert body == ""

    def test_decode_request_body_invalid_utf8(self):
        """Test that invalid UTF-8 returns empty string and logs warning."""
        # Create invalid UTF-8 sequence
        invalid_utf8 = b"\x80\x81\x82"
        encoded = base64.b64encode(invalid_utf8).decode("utf-8")
        event = {"body": encoded, "isBase64Encoded": True}

        body = TwilioSignatureValidator._decode_request_body(event)
        assert body == ""

    def test_decode_request_body_empty(self):
        """Test decoding empty body."""
        event = {"body": "", "isBase64Encoded": False}

        body = TwilioSignatureValidator._decode_request_body(event)
        assert body == ""

    def test_decode_request_body_missing(self):
        """Test decoding when body is missing from event."""
        event = {}

        body = TwilioSignatureValidator._decode_request_body(event)
        assert body == ""

    def test_validate_form_encoded_content_type(self):
        """Test that form-encoded content type is detected (case-insensitive)."""
        validator = TwilioSignatureValidator("test_token")
        validator.request_validator.validate = Mock(return_value=True)

        # Test with various casings
        for content_type in [
            "application/x-www-form-urlencoded",
            "Application/X-WWW-Form-URLEncoded",
            "application/x-www-form-urlencoded; charset=utf-8",
        ]:
            event = {
                "headers": {
                    "x-twilio-signature": "test_sig",
                    "host": "example.com",
                    "content-type": content_type,
                },
                "rawPath": "/webhook",
                "body": "CallSid=123&From=456",
            }

            result = validator.validate(event)
            assert result is True

            # Verify the validator was called with a dict (form-encoded)
            call_args = validator.request_validator.validate.call_args
            validation_data = call_args[0][1]
            assert isinstance(validation_data, dict)

    def test_validate_json_content_type(self):
        """Test that JSON content type uses body string."""
        validator = TwilioSignatureValidator("test_token")
        validator.request_validator.validate = Mock(return_value=True)

        event = {
            "headers": {
                "x-twilio-signature": "test_sig",
                "host": "example.com",
                "content-type": "application/json",
            },
            "rawPath": "/webhook",
            "body": '{"test": "data"}',
        }

        result = validator.validate(event)
        assert result is True

        # Verify the validator was called with a string (JSON)
        call_args = validator.request_validator.validate.call_args
        validation_data = call_args[0][1]
        assert isinstance(validation_data, str)
        assert validation_data == '{"test": "data"}'

    def test_validate_invalid_signature(self):
        """Test that invalid signature returns False and logs warning."""
        validator = TwilioSignatureValidator("test_token")
        validator.request_validator.validate = Mock(return_value=False)

        event = {
            "headers": {
                "x-twilio-signature": "invalid_sig",
                "host": "example.com",
            },
            "rawPath": "/webhook",
            "body": "",
        }

        result = validator.validate(event)
        assert result is False

    def test_validate_none_headers_dict(self):
        """Test that None headers dict is handled gracefully."""
        validator = TwilioSignatureValidator("test_token")

        # Headers is None (can happen in some API Gateway configurations)
        event = {"headers": None, "rawPath": "/webhook", "body": ""}

        result = validator.validate(event)
        assert result is False  # Should fail due to missing signature

    def test_validate_none_header_values(self):
        """Test that None header values are handled gracefully."""
        validator = TwilioSignatureValidator("test_token")
        validator.request_validator.validate = Mock(return_value=True)

        # Some headers have None values
        event = {
            "headers": {
                "x-twilio-signature": "test_sig",
                "host": "example.com",
                "content-type": None,  # None value
            },
            "rawPath": "/webhook",
            "body": "test",
        }

        result = validator.validate(event)
        assert result is True

    def test_construct_url_empty_query_string(self):
        """Test URL construction with empty query string."""
        event = {
            "rawPath": "/webhook",
            "rawQueryString": "",
        }
        headers = {"host": "api.example.com"}

        url = TwilioSignatureValidator._construct_request_url(event, headers)
        assert url == "https://api.example.com/webhook"
