"""AWS Lambda proxy handlers for Twilio webhooks."""

__all__ = []

try:
    from .agentcore_lambda import AgentCoreLambdaProxy  # noqa: F401

    __all__.append("AgentCoreLambdaProxy")
except ModuleNotFoundError as e:
    # Only catch missing boto3/bedrock_agentcore dependencies
    # Re-raise if it's a bug in our code
    if e.name not in ("boto3", "botocore", "bedrock_agentcore"):
        raise

try:
    from .validation import TwilioSignatureValidator  # noqa: F401

    __all__.append("TwilioSignatureValidator")
except ModuleNotFoundError as e:
    # Only catch missing twilio dependency
    # Re-raise if it's a bug in our code
    if e.name != "twilio":
        raise
