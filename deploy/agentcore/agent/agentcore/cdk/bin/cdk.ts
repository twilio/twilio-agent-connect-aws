#!/usr/bin/env node
import { AgentCoreStack } from '../lib/cdk-stack';
import { ConfigIO } from '@aws/agentcore-cdk';
import { App } from 'aws-cdk-lib';
import * as path from 'path';
import * as fs from 'fs';
import { loadEnvConfig, toAgentCoreEnvVars } from './env-config';

const STACK_NAME = 'TacAgentCoreCliStack';

async function main() {
  // Config root is parent of cdk/ directory. The CLI sets process.cwd() to agentcore/cdk/.
  const configRoot = path.resolve(process.cwd(), '..');

  // Ensure aws-targets.json exists (CLI requires it, even if empty)
  const awsTargetsPath = path.resolve(configRoot, 'aws-targets.json');
  if (!fs.existsSync(awsTargetsPath)) {
    fs.writeFileSync(awsTargetsPath, '[]', 'utf-8');
  }
  const configIO = new ConfigIO({ baseDir: configRoot });

  // Load and validate environment configuration
  const envConfig = loadEnvConfig(configRoot);

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

  new AgentCoreStack(app, STACK_NAME, {
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

  app.synth();
}

main().catch((error: unknown) => {
  console.error('AgentCore CDK synthesis failed:', error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
