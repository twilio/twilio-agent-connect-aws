import * as dotenv from 'dotenv';
import * as path from 'path';

/**
 * Environment configuration for TAC AgentCore deployment.
 * Reads from /deploy/agentcore/.env and validates required variables.
 */

export interface TacEnvConfig {
  // AWS Configuration
  awsAccountId: string;
  awsRegion: string;

  // Twilio Configuration
  twilioAccountSid: string;
  twilioAuthToken: string;
  twilioApiKey: string;
  twilioApiSecret: string;
  twilioPhoneNumber: string;
  twilioConversationConfigurationId: string;
  twilioLogLevel: string;
}

/**
 * Loads and validates environment variables from .env file.
 *
 * @param configRoot - Path to agentcore/ directory
 * @returns Validated environment configuration
 * @throws Error if required variables are missing
 */
export function loadEnvConfig(configRoot: string): TacEnvConfig {
  // Load environment variables from /deploy/agentcore_aws_lambda/.env (centralized)
  // configRoot is agentcore/, so we go up 2 levels to reach agentcore_aws_lambda/
  const envPath = path.resolve(configRoot, '../../.env');
  dotenv.config({ path: envPath });

  // Validate required environment variables
  const requiredVars = [
    'AWS_ACCOUNT_ID',
    'AWS_REGION',
    'TWILIO_ACCOUNT_SID',
    'TWILIO_AUTH_TOKEN',
    'TWILIO_API_KEY',
    'TWILIO_API_SECRET',
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
    twilioAccountSid: process.env.TWILIO_ACCOUNT_SID!,
    twilioAuthToken: process.env.TWILIO_AUTH_TOKEN!,
    twilioApiKey: process.env.TWILIO_API_KEY!,
    twilioApiSecret: process.env.TWILIO_API_SECRET!,
    twilioPhoneNumber: process.env.TWILIO_PHONE_NUMBER!,
    twilioConversationConfigurationId: process.env.TWILIO_CONVERSATION_CONFIGURATION_ID!,
    twilioLogLevel: process.env.TWILIO_LOG_LEVEL || 'INFO',
  };
}

/**
 * Converts TacEnvConfig to AgentCore envVars format.
 *
 * @param config - Validated environment configuration
 * @returns Array of environment variables for AgentCore runtime
 */
export function toAgentCoreEnvVars(config: TacEnvConfig): Array<{ name: string; value: string }> {
  return [
    { name: 'TWILIO_ACCOUNT_SID', value: config.twilioAccountSid },
    { name: 'TWILIO_AUTH_TOKEN', value: config.twilioAuthToken },
    { name: 'TWILIO_API_KEY', value: config.twilioApiKey },
    { name: 'TWILIO_API_SECRET', value: config.twilioApiSecret },
    { name: 'TWILIO_PHONE_NUMBER', value: config.twilioPhoneNumber },
    { name: 'TWILIO_CONVERSATION_CONFIGURATION_ID', value: config.twilioConversationConfigurationId },
    { name: 'TWILIO_LOG_LEVEL', value: config.twilioLogLevel },
  ];
}
