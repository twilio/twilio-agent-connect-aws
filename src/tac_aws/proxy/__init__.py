"""AWS Lambda proxy handlers for Twilio webhooks."""

__all__ = []

try:
    from .agentcore_lambda import AgentCoreLambdaProxy  # noqa: F401

    __all__.append("AgentCoreLambdaProxy")
except ModuleNotFoundError as e:
    # Only catch missing agentcore dependencies (boto3, botocore, bedrock_agentcore, etc.)
    # Re-raise if it's a bug in our code (internal tac_aws import path error)
    if e.name is not None and e.name.startswith("tac_aws."):
        raise

try:
    from .validation import TwilioSignatureValidator  # noqa: F401

    __all__.append("TwilioSignatureValidator")
except ModuleNotFoundError as e:
    # Only catch missing twilio dependencies (twilio, etc.)
    # Re-raise if it's a bug in our code (internal tac_aws import path error)
    if e.name is not None and e.name.startswith("tac_aws."):
        raise
