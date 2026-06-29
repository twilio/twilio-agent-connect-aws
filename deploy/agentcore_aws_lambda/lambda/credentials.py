"""
Credentials Management - Fetch Twilio credentials from AWS Secrets Manager.

This module provides utilities for securely retrieving Twilio credentials
from AWS Secrets Manager for use in Lambda functions.
"""

import json
import os

import boto3
from tac.core.logging import get_logger

logger = get_logger(__name__)


def fetch_twilio_auth_token(secret_arn: str, region: str | None = None) -> str:
    """Fetch Twilio auth token from Secrets Manager.

    Args:
        secret_arn: ARN of the secret containing Twilio credentials
        region: AWS region for Secrets Manager client (optional, defaults to
            AWS_REGION environment variable provided by Lambda runtime)

    Returns:
        Twilio auth token string

    Raises:
        ValueError: If TWILIO_AUTH_TOKEN is missing or empty
        Exception: If Secrets Manager fetch fails
    """
    # Lambda runtime automatically provides AWS_REGION environment variable
    aws_region = region or os.environ["AWS_REGION"]
    secrets_client = boto3.client("secretsmanager", region_name=aws_region)

    try:
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        credentials = json.loads(response["SecretString"])

        # Validate and extract auth token
        auth_token = credentials.get("TWILIO_AUTH_TOKEN")
        if not auth_token:
            raise ValueError(
                "Secret missing TWILIO_AUTH_TOKEN. "
                "Run 'make secret-update' to populate Twilio credentials."
            )

        logger.info("Successfully loaded Twilio auth token from Secrets Manager")
        return auth_token

    except Exception as e:
        logger.error(f"Failed to fetch Twilio auth token: {e}", exc_info=True)
        raise
