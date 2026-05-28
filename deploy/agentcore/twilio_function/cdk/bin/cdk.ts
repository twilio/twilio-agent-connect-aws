#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { TacAgentcoreTwilioFunctionStack } from '../lib/cdk-stack';
import { loadEnvConfig } from './env-config';

const app = new cdk.App();

// Load and validate environment configuration
const config = loadEnvConfig(__dirname);

new TacAgentcoreTwilioFunctionStack(app, 'TacAgentcoreTwilioFunctionStack', {
  env: {
    account: config.awsAccountId || process.env.CDK_DEFAULT_ACCOUNT,
    region: config.awsRegion,
  },
  description: 'TAC Twilio Function deployment infrastructure for AgentCore integration',
});
