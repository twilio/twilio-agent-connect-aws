import * as dotenv from 'dotenv';
import * as path from 'path';

/**
 * Environment configuration for Lambda deployment.
 * Reads from /deploy/agentcore/.env and validates required variables.
 */

export interface LambdaEnvConfig {
  // AgentCore Configuration
  agentCoreRuntimeArn: string;

  // Twilio Configuration
  twilioConversationConfigurationId: string;
  twilioAuthToken: string;

  // AWS Configuration
  awsAccountId: string;
  awsRegion: string;
}

/**
 * Loads and validates environment variables from .env file.
 *
 * @param configRoot - Path to aws_lambda/cdk directory
 * @returns Validated environment configuration
 * @throws Error if required variables are missing
 */
export function loadEnvConfig(configRoot: string): LambdaEnvConfig {
  // Load environment variables from /deploy/agentcore/aws_lambda/.env
  const envPath = path.resolve(configRoot, '../../.env');
  dotenv.config({ path: envPath });

  // Validate required environment variables
  const requiredVars = [
    'AGENTCORE_RUNTIME_ARN',
    'TWILIO_CONVERSATION_CONFIGURATION_ID',
    'TWILIO_AUTH_TOKEN',
    'AWS_REGION',
    'AWS_ACCOUNT_ID',
  ];

  const missingVars = requiredVars.filter(varName => !process.env[varName]);
  if (missingVars.length > 0) {
    throw new Error(
      `Missing required environment variables in .env file:\n` +
      missingVars.map(v => `  - ${v}`).join('\n') +
      `\n\nPlease set these in: ${envPath}`
    );
  }

  // Return validated configuration
  return {
    agentCoreRuntimeArn: process.env.AGENTCORE_RUNTIME_ARN!,
    twilioConversationConfigurationId: process.env.TWILIO_CONVERSATION_CONFIGURATION_ID!,
    twilioAuthToken: process.env.TWILIO_AUTH_TOKEN!,
    awsAccountId: process.env.AWS_ACCOUNT_ID!,
    awsRegion: process.env.AWS_REGION!,
  };
}
