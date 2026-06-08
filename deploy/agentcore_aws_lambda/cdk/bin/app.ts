#!/usr/bin/env node
import { AgentCoreStack } from '../lib/agentcore-stack';
import { LambdaStack } from '../lib/lambda-stack';
import { ConfigIO } from '@aws/agentcore-cdk';
import { App } from 'aws-cdk-lib';
import * as path from 'path';
import { loadEnvConfig, toAgentCoreEnvVars } from '../config/env-config';

const STACK_NAME = 'TacAgentCoreStack';

async function main() {
  // baseDir should point to the agentcore/ directory itself
  // ConfigIO expects baseDir to be the config root (agentcore/ directory)
  const configRoot = path.join(process.cwd(), 'agentcore');

  const configIO = new ConfigIO({ baseDir: configRoot });

  // Load and validate environment configuration
  const envConfig = loadEnvConfig(process.cwd());

  // Read agentcore.json
  const spec = await configIO.readProjectSpec();

  // Inject Twilio env vars into spec
  const twilioEnvVars = toAgentCoreEnvVars(envConfig);
  const enhancedSpec = {
    ...spec,
    runtimes: spec.runtimes.map(runtime => ({
      ...runtime,
      envVars: [...(runtime.envVars || []), ...twilioEnvVars]
    }))
  };

  const app = new App();

  // Stack 1: AgentCore Runtime
  const agentCoreStack = new AgentCoreStack(app, STACK_NAME, {
    spec: enhancedSpec,
    env: {
      account: envConfig.awsAccountId,
      region: envConfig.awsRegion,
    },
    description: `TAC AgentCore stack for Twilio Agent Connect (${envConfig.awsRegion})`,
    tags: {
      'agentcore:project-name': spec.name,
      'tac:deployment': 'agentcore',
    },
  });

  // Stack 2: Lambda Webhook Proxy (depends on AgentCore)
  const lambdaStack = new LambdaStack(app, 'TacLambdaStack', {
    agentCoreRuntimeArn: agentCoreStack.runtimeArn,  // Cross-stack reference!
    twilioConversationConfigurationId: envConfig.twilioConversationConfigurationId,
    twilioAuthToken: envConfig.twilioAuthToken,
    env: {
      account: envConfig.awsAccountId,
      region: envConfig.awsRegion,
    },
    description: 'TAC Lambda Webhook Proxy for Twilio Agent Connect',
  });

  // Explicit dependency (CDK infers this from runtimeArn reference, but being explicit is clearer)
  lambdaStack.addDependency(agentCoreStack);

  app.synth();
}

main().catch((error: unknown) => {
  console.error('AgentCore CDK synthesis failed:', error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
