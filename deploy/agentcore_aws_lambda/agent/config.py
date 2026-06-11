"""
Configuration loader for TAC.
"""
import json
import os
import boto3
from tac import TACConfig
from tac.core.logging import get_logger

logger = get_logger(__name__)


def load_tac_config() -> TACConfig:
    """Load TAC configuration from Secrets Manager."""
    twilio_secret_arn = os.environ.get('TWILIO_SECRET_ARN')

    if not twilio_secret_arn:
        raise ValueError(
            "TWILIO_SECRET_ARN environment variable is required. "
            "This should be set automatically by the CDK stack."
        )

    # Load from Secrets Manager
    logger.info("Loading Twilio credentials from Secrets Manager")
    secrets_client = boto3.client('secretsmanager')
    response = secrets_client.get_secret_value(SecretId=twilio_secret_arn)
    secrets = json.loads(response['SecretString'])

    return TACConfig(
        account_sid=secrets['TWILIO_ACCOUNT_SID'],
        auth_token=secrets['TWILIO_AUTH_TOKEN'],
        api_key=secrets['TWILIO_API_KEY'],
        api_secret=secrets['TWILIO_API_SECRET'],
        phone_number=secrets['TWILIO_PHONE_NUMBER'],
        conversation_configuration_id=secrets['TWILIO_CONVERSATION_CONFIGURATION_ID'],
        log_level=os.environ.get('TWILIO_LOG_LEVEL', 'INFO'),
    )
