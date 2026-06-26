import * as dotenv from 'dotenv';
import * as path from 'path';

/**
 * Environment configuration for TAC AgentCore deployment.
 * Reads from /deploy/agentcore_aws_lambda/.env and validates required variables.
 */

export interface TacEnvConfig {
  // AWS Configuration
  awsAccountId: string;
  awsRegion: string;
  // Twilio Configuration (non-secret)
  twilioPhoneNumber: string;
  twilioConversationConfigurationId: string;
}

/**
 * Loads and validates environment variables from .env file.
 *
 * @param configRoot - Path to cdk/ directory
 * @returns Validated environment configuration
 * @throws Error if required variables are missing
 */
export function loadEnvConfig(configRoot: string): TacEnvConfig {
  // Load environment variables from /deploy/agentcore_aws_lambda/.env (centralized)
  // configRoot is cdk/, so we go up 1 level to reach agentcore_aws_lambda/
  const envPath = path.resolve(configRoot, '../.env');
  dotenv.config({ path: envPath });

  // Validate required environment variables
  const requiredVars = [
    'AWS_ACCOUNT_ID',
    'AWS_REGION',
    'TWILIO_PHONE_NUMBER',
    'TWILIO_CONVERSATION_CONFIGURATION_ID',
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
    awsAccountId: process.env.AWS_ACCOUNT_ID!,
    awsRegion: process.env.AWS_REGION!,
    twilioPhoneNumber: process.env.TWILIO_PHONE_NUMBER!,
    twilioConversationConfigurationId: process.env.TWILIO_CONVERSATION_CONFIGURATION_ID!,
  };
}

