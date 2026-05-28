import * as dotenv from 'dotenv';
import * as path from 'path';

/**
 * Environment configuration for Twilio Function IAM deployment.
 * Reads from /deploy/agentcore/twilio_function/.env and validates required variables.
 */

export interface TwilioFunctionEnvConfig {
  // AWS Configuration
  awsAccountId: string;
  awsRegion: string;
}

/**
 * Loads and validates environment variables from .env file.
 *
 * @param configRoot - Path to twilio_function/cdk directory
 * @returns Validated environment configuration
 * @throws Error if required variables are missing
 */
export function loadEnvConfig(configRoot: string): TwilioFunctionEnvConfig {
  // Load environment variables from /deploy/agentcore/twilio_function/.env
  const envPath = path.resolve(configRoot, '../../.env');
  dotenv.config({ path: envPath });

  // Validate required environment variables
  const requiredVars = [
    'AWS_REGION',
  ];

  const missingVars = requiredVars.filter(varName => !process.env[varName]);
  if (missingVars.length > 0) {
    throw new Error(
      `Missing required environment variables in .env file:\n` +
      missingVars.map(v => `  - ${v}`).join('\n') +
      `\n\nPlease set these in: ${envPath}`
    );
  }

  // AWS_ACCOUNT_ID is optional - CDK can detect it from credentials
  const awsAccountId = process.env.AWS_ACCOUNT_ID || process.env.CDK_DEFAULT_ACCOUNT || '';

  // Return validated configuration
  return {
    awsAccountId,
    awsRegion: process.env.AWS_REGION!,
  };
}
