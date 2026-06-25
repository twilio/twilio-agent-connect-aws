#!/usr/bin/env node
import { AgentCoreStack } from '../lib/agentcore-stack';
import { LambdaStack } from '../lib/lambda-stack';
import { SecretsStack } from '../lib/secrets-stack';
import { ConfigIO } from '@aws/agentcore-cdk';
import { App } from 'aws-cdk-lib';
import * as path from 'path';
import { loadEnvConfig } from '../config/env-config';

async function main() {
  const configRoot = path.join(process.cwd(), 'agentcore');
  const configIO = new ConfigIO({ baseDir: configRoot });
  const envConfig = loadEnvConfig(process.cwd());
  const spec = await configIO.readProjectSpec();

  const app = new App();

  // Create Secrets Manager stack (first - other stacks depend on it)
  const secretsStack = new SecretsStack(app, 'TacSecretsStack', {
    env: {
      account: envConfig.awsAccountId,
      region: envConfig.awsRegion,
    },
    description: 'TAC Secrets Manager for Twilio credentials',
  });

  // Inject secret ARN as env var into AgentCore runtime
  const enhancedSpec = {
    ...spec,
    runtimes: spec.runtimes.map(runtime => ({
      ...runtime,
      envVars: [
        ...(runtime.envVars || []),
        { name: 'TWILIO_SECRET_ARN', value: secretsStack.twilioSecret.secretArn },
      ]
    }))
  };

  const agentCoreStack = new AgentCoreStack(app, 'TacAgentCoreStack', {
    spec: enhancedSpec,
    twilioSecret: secretsStack.twilioSecret,
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
    twilioSecret: secretsStack.twilioSecret,
    env: {
      account: envConfig.awsAccountId,
      region: envConfig.awsRegion,
    },
    description: 'TAC Lambda Webhook Proxy for Twilio Agent Connect',
  });

  // Stack dependencies
  agentCoreStack.addDependency(secretsStack);
  lambdaStack.addDependency(agentCoreStack);

  app.synth();
}

main().catch((error: unknown) => {
  console.error('AgentCore CDK synthesis failed:', error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
