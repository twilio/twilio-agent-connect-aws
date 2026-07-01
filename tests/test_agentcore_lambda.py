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
