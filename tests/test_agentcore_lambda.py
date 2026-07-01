"""Tests for AgentCoreLambdaProxy."""

import pytest

# Check if agentcore dependencies are available
try:
    from tac_aws.proxy import AgentCoreLambdaProxy

    AGENTCORE_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    AGENTCORE_AVAILABLE = False

# Skip all tests if agentcore dependencies not installed
pytestmark = pytest.mark.skipif(
    not AGENTCORE_AVAILABLE,
    reason="agentcore dependencies not installed (optional)",
)


class TestAgentCoreLambdaProxy:
    """Test AgentCoreLambdaProxy functionality."""

    def test_normalize_headers_none_dict(self):
        """Test that _normalize_headers handles None headers dict."""
        proxy = AgentCoreLambdaProxy(
            agentcore_runtime_arn="arn:aws:bedrock:us-east-1:123456789012:runtime/test",
            conversation_configuration_id="test-config",
            twilio_auth_token="test_token",
            aws_region="us-east-1",
        )

        result = proxy._normalize_headers(None)
        assert result == {}

    def test_normalize_headers_none_values(self):
        """Test that _normalize_headers handles None header values."""
        proxy = AgentCoreLambdaProxy(
            agentcore_runtime_arn="arn:aws:bedrock:us-east-1:123456789012:runtime/test",
            conversation_configuration_id="test-config",
            twilio_auth_token="test_token",
            aws_region="us-east-1",
        )

        headers = {
            "Content-Type": "application/json",
            "X-Custom-Header": None,
            "Host": "example.com",
        }

        result = proxy._normalize_headers(headers)
        assert result == {
            "content-type": "application/json",
            "x-custom-header": "",
            "host": "example.com",
        }

    def test_normalize_headers_case_insensitive(self):
        """Test that _normalize_headers lowercases keys."""
        proxy = AgentCoreLambdaProxy(
            agentcore_runtime_arn="arn:aws:bedrock:us-east-1:123456789012:runtime/test",
            conversation_configuration_id="test-config",
            twilio_auth_token="test_token",
            aws_region="us-east-1",
        )

        headers = {
            "Content-Type": "application/json",
            "X-Twilio-Signature": "abc123",
            "HOST": "example.com",
        }

        result = proxy._normalize_headers(headers)
        assert result == {
            "content-type": "application/json",
            "x-twilio-signature": "abc123",
            "host": "example.com",
        }

    def test_normalize_headers_empty_dict(self):
        """Test that _normalize_headers handles empty dict."""
        proxy = AgentCoreLambdaProxy(
            agentcore_runtime_arn="arn:aws:bedrock:us-east-1:123456789012:runtime/test",
            conversation_configuration_id="test-config",
            twilio_auth_token="test_token",
            aws_region="us-east-1",
        )

        result = proxy._normalize_headers({})
        assert result == {}

    def test_extract_call_sid_from_post_body(self):
        """Test that _extract_call_sid extracts CallSid from POST body."""
        proxy = AgentCoreLambdaProxy(
            agentcore_runtime_arn="arn:aws:bedrock:us-east-1:123456789012:runtime/test",
            conversation_configuration_id="test-config",
            twilio_auth_token="test_token",
            aws_region="us-east-1",
        )

        event = {
            "body": "CallSid=CA1234567890abcdef&From=%2B15551234567",
            "isBase64Encoded": False,
        }

        call_sid = proxy._extract_call_sid(event)
        assert call_sid == "CA1234567890abcdef"

    def test_extract_call_sid_missing(self):
        """Test that _extract_call_sid returns None when CallSid is missing."""
        proxy = AgentCoreLambdaProxy(
            agentcore_runtime_arn="arn:aws:bedrock:us-east-1:123456789012:runtime/test",
            conversation_configuration_id="test-config",
            twilio_auth_token="test_token",
            aws_region="us-east-1",
        )

        event = {
            "body": "From=%2B15551234567",
            "isBase64Encoded": False,
        }

        call_sid = proxy._extract_call_sid(event)
        assert call_sid is None

    def test_extract_call_sid_base64_encoded(self):
        """Test that _extract_call_sid handles base64-encoded bodies."""
        import base64

        proxy = AgentCoreLambdaProxy(
            agentcore_runtime_arn="arn:aws:bedrock:us-east-1:123456789012:runtime/test",
            conversation_configuration_id="test-config",
            twilio_auth_token="test_token",
            aws_region="us-east-1",
        )

        body_content = "CallSid=CA1234567890abcdef&From=%2B15551234567"
        encoded_body = base64.b64encode(body_content.encode("utf-8")).decode("utf-8")

        event = {
            "body": encoded_body,
            "isBase64Encoded": True,
        }

        call_sid = proxy._extract_call_sid(event)
        assert call_sid == "CA1234567890abcdef"

    def test_extract_call_sid_none_body(self):
        """Test that _extract_call_sid handles None body gracefully."""
        proxy = AgentCoreLambdaProxy(
            agentcore_runtime_arn="arn:aws:bedrock:us-east-1:123456789012:runtime/test",
            conversation_configuration_id="test-config",
            twilio_auth_token="test_token",
            aws_region="us-east-1",
        )

        event = {
            "body": None,  # AWS events can have body: null
        }

        call_sid = proxy._extract_call_sid(event)
        assert call_sid is None
