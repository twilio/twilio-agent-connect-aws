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


VOICE_EVENT = {
    "rawPath": "/twiml",
    "body": "CallSid=CA1234567890abcdef&From=%2B15551234567&CallerCountry=MX",
    "isBase64Encoded": False,
}


def _twiml_proxy(**kwargs):
    """Proxy with signature validation and the presigned URL stubbed out."""
    from unittest.mock import MagicMock

    proxy = AgentCoreLambdaProxy(
        agentcore_runtime_arn="arn:aws:bedrock:us-east-1:123456789012:runtime/test",
        conversation_configuration_id="test-config",
        twilio_auth_token="test_token",
        aws_region="us-east-1",
        **kwargs,
    )
    proxy.signature_validator.validate = MagicMock(return_value=True)
    proxy.agentcore_runtime_client = MagicMock()
    proxy.agentcore_runtime_client.generate_presigned_url.return_value = "wss://presigned.test/ws"
    return proxy


class TestAgentCoreLambdaProxyTwiML:
    """TwiML generation and customization on the voice route."""

    def test_defaults_emit_presigned_url_and_configuration(self):
        response = _twiml_proxy().lambda_handler(VOICE_EVENT, None)

        assert response["statusCode"] == 200
        assert 'url="wss://presigned.test/ws"' in response["body"]
        assert 'conversationConfiguration="test-config"' in response["body"]

    def test_static_twiml_options_applied(self):
        from tac.models.voice import TwiMLOptions

        proxy = _twiml_proxy(
            twiml_options=TwiMLOptions(welcome_greeting="Hi there!", interruptible="speech")
        )
        body = proxy.lambda_handler(VOICE_EVENT, None)["body"]

        assert 'welcomeGreeting="Hi there!"' in body
        assert 'interruptible="speech"' in body
        # Proxy defaults survive a layer that doesn't mention them
        assert 'url="wss://presigned.test/ws"' in body
        assert 'conversationConfiguration="test-config"' in body

    def test_twiml_options_accepts_dict(self):
        proxy = _twiml_proxy(twiml_options={"welcome_greeting": "From a dict"})
        assert 'welcomeGreeting="From a dict"' in proxy.lambda_handler(VOICE_EVENT, None)["body"]

    def test_sync_customizer_overrides_static_options(self):
        from tac.models.voice import TwiMLOptions, TwiMLRequest

        seen = {}

        def by_country(req: TwiMLRequest) -> TwiMLOptions:
            seen["country"] = req.caller_country
            seen["call_sid"] = req.call_sid
            if req.caller_country == "MX":
                return TwiMLOptions(language="es-MX", welcome_greeting="¡Hola!")
            return TwiMLOptions()

        proxy = _twiml_proxy(
            twiml_options=TwiMLOptions(welcome_greeting="Hi there!", voice="en-US-Journey-O")
        )
        proxy.on_inbound_call_twiml(by_country)
        body = proxy.lambda_handler(VOICE_EVENT, None)["body"]

        assert seen == {"country": "MX", "call_sid": "CA1234567890abcdef"}
        assert 'welcomeGreeting="¡Hola!"' in body
        assert 'language="es-MX"' in body
        # Unset by the customizer, so the static layer still wins
        assert 'voice="en-US-Journey-O"' in body

    def test_async_customizer_supported(self):
        from tac.models.voice import TwiMLOptions, TwiMLRequest

        async def customize(req: TwiMLRequest) -> TwiMLOptions:
            return TwiMLOptions(welcome_greeting="From async")

        proxy = _twiml_proxy()
        proxy.on_inbound_call_twiml(customize)

        assert 'welcomeGreeting="From async"' in proxy.lambda_handler(VOICE_EVENT, None)["body"]

    def test_customizer_can_override_websocket_url(self):
        from tac.models.voice import TwiMLOptions, TwiMLRequest

        def customize(req: TwiMLRequest) -> TwiMLOptions:
            return TwiMLOptions(websocket_url="wss://custom.test/ws")

        proxy = _twiml_proxy()
        proxy.on_inbound_call_twiml(customize)

        assert 'url="wss://custom.test/ws"' in proxy.lambda_handler(VOICE_EVENT, None)["body"]

    def test_missing_call_sid_returns_400(self):
        proxy = _twiml_proxy()
        event = {**VOICE_EVENT, "body": "From=%2B15551234567"}

        assert proxy.lambda_handler(event, None)["statusCode"] == 400
