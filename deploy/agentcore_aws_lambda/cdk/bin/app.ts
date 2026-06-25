#!/usr/bin/env node
import { AgentCoreStack } from '../lib/agentcore-stack';
import { LambdaStack } from '../lib/lambda-stack';
import { ConfigIO } from '@aws/agentcore-cdk';
import { App } from 'aws-cdk-lib';
import * as path from 'path';
import { loadEnvConfig, toAgentCoreEnvVars } from '../config/env-config';

async function main() {
  const configRoot = path.join(process.cwd(), 'agentcore');
  const configIO = new ConfigIO({ baseDir: configRoot });
  const envConfig = loadEnvConfig(process.cwd());
  const spec = await configIO.readProjectSpec();

  // Inject Twilio credentials as env vars into AgentCore runtime
  const twilioEnvVars = toAgentCoreEnvVars(envConfig);
  const enhancedSpec = {
    ...spec,
    runtimes: spec.runtimes.map(runtime => ({
      ...runtime,
      envVars: [...(runtime.envVars || []), ...twilioEnvVars]
    }))
  };

  const app = new App();

  const agentCoreStack = new AgentCoreStack(app, 'TacAgentCoreStack', {
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

  const lambdaStack = new LambdaStack(app, 'TacLambdaStack', {
    agentCoreRuntimeArn: agentCoreStack.runtimeArn,
    twilioConversationConfigurationId: envConfig.twilioConversationConfigurationId,
    twilioAuthToken: envConfig.twilioAuthToken,
    env: {
      account: envConfig.awsAccountId,
      region: envConfig.awsRegion,
    },
    description: 'TAC Lambda Webhook Proxy for Twilio Agent Connect',
  });

  // Lambda must deploy after AgentCore to use runtime ARN
  lambdaStack.addDependency(agentCoreStack);

  app.synth();
}

main().catch((error: unknown) => {
  console.error('AgentCore CDK synthesis failed:', error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
