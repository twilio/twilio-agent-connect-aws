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
        region: AWS region for Secrets Manager client (optional, auto-detected from
            AWS_REGION env var, boto3 session, or AWS config)

    Returns:
        Twilio auth token string

    Raises:
        ValueError: If TWILIO_AUTH_TOKEN is missing or empty, or if AWS region cannot be determined
        Exception: If Secrets Manager fetch fails
    """
    # Resolve AWS region: explicit parameter > AWS_REGION env var > boto3 session
    aws_region = region or os.environ.get("AWS_REGION") or boto3.Session().region_name

    if not aws_region:
        raise ValueError("AWS region not found. Provide region parameter or configure AWS region.")

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
