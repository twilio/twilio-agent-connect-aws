"""
Secrets Manager integration for TAC AgentCore deployment.

Fetches Twilio credentials from AWS Secrets Manager and provides
them for TAC configuration.
"""

import json
import os

import boto3
from tac import TACConfig
from tac.core.logging import get_logger

logger = get_logger(__name__)


def get_twilio_credentials() -> dict:
    """
    Fetch Twilio credentials from AWS Secrets Manager.

    Uses TWILIO_SECRET_ARN environment variable to locate the secret.

    Returns:
        dict: Twilio credentials dictionary with keys:
            - TWILIO_ACCOUNT_SID
            - TWILIO_AUTH_TOKEN
            - TWILIO_API_KEY
            - TWILIO_API_SECRET
            - TWILIO_PHONE_NUMBER
            - TWILIO_CONVERSATION_CONFIGURATION_ID

    Raises:
        KeyError: If TWILIO_SECRET_ARN environment variable is not set
        Exception: If secret retrieval fails
    """
    secret_arn = os.environ["TWILIO_SECRET_ARN"]
    aws_region = os.environ.get("AWS_REGION", "us-east-1")

    secrets_client = boto3.client("secretsmanager", region_name=aws_region)

    try:
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        credentials = json.loads(response["SecretString"])
        logger.info("Successfully loaded Twilio credentials from Secrets Manager")
        return credentials
    except Exception as e:
        logger.error(f"Failed to fetch Twilio credentials from Secrets Manager: {e}", exc_info=True)
        raise


def create_tac_config() -> TACConfig:
    """
    Create TACConfig from credentials stored in AWS Secrets Manager.

    Returns:
        TACConfig: Configured TAC instance ready for use

    Raises:
        KeyError: If TWILIO_SECRET_ARN is not set
        Exception: If secret retrieval or config creation fails
    """
    credentials = get_twilio_credentials()

    return TACConfig(
        account_sid=credentials["TWILIO_ACCOUNT_SID"],
        auth_token=credentials["TWILIO_AUTH_TOKEN"],
        api_key=credentials["TWILIO_API_KEY"],
        api_secret=credentials["TWILIO_API_SECRET"],
        phone_number=credentials["TWILIO_PHONE_NUMBER"],
        conversation_configuration_id=credentials["TWILIO_CONVERSATION_CONFIGURATION_ID"],
    )
