"""Secrets Manager integration for TAC AgentCore deployment."""

import json
import os

import boto3
from tac import TACConfig
from tac.core.logging import get_logger

logger = get_logger(__name__)


def get_twilio_credentials() -> dict:
    """Fetch Twilio credentials from AWS Secrets Manager."""
    secret_arn = os.environ["TWILIO_SECRET_ARN"]
    secrets_client = boto3.client("secretsmanager", region_name=os.environ["AWS_REGION"])

    try:
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        credentials = json.loads(response["SecretString"])
        logger.info("Successfully loaded Twilio credentials from Secrets Manager")
        return credentials
    except Exception as e:
        logger.error(f"Failed to fetch Twilio credentials from Secrets Manager: {e}", exc_info=True)
        raise


def create_tac_config() -> TACConfig:
    """Create TACConfig from Secrets Manager (credentials) and environment variables (configuration)."""
    credentials = get_twilio_credentials()

    return TACConfig(
        account_sid=credentials["TWILIO_ACCOUNT_SID"],
        auth_token=credentials["TWILIO_AUTH_TOKEN"],
        api_key=credentials["TWILIO_API_KEY"],
        api_secret=credentials["TWILIO_API_SECRET"],
        phone_number=os.environ["TWILIO_PHONE_NUMBER"],
        conversation_configuration_id=os.environ["TWILIO_CONVERSATION_CONFIGURATION_ID"],
    )
