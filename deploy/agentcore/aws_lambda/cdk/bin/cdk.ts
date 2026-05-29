#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { LambdaStack } from '../lib/cdk-stack';
import { loadEnvConfig } from './env-config';

const app = new cdk.App();

// Load and validate environment configuration
const config = loadEnvConfig(__dirname);

new LambdaStack(app, 'TacAgentcoreLambdaStack', {
  agentCoreRuntimeArn: config.agentCoreRuntimeArn,
  twilioConversationConfigurationId: config.twilioConversationConfigurationId,
  twilioAuthToken: config.twilioAuthToken,
  env: {
    account: config.awsAccountId,
    region: config.awsRegion,
  },
  description: 'TAC Webhook Proxy Lambda for Twilio Agent Connect',
});
