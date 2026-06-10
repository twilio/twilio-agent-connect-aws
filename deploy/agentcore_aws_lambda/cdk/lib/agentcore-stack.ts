import {
  AgentCoreApplication,
  type AgentCoreProjectSpec,
} from '@aws/agentcore-cdk';
import { CfnOutput, Stack, type StackProps } from 'aws-cdk-lib';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

export interface AgentCoreStackProps extends StackProps {
  /**
   * The AgentCore project specification containing agents, memories, and credentials.
   */
  spec: AgentCoreProjectSpec;

  /**
   * ARN of the Secrets Manager secret containing Twilio credentials.
   */
  twilioSecretArn: string;
}

/**
 * CDK Stack that deploys AgentCore infrastructure.
 *
 * This is a thin wrapper that instantiates L3 constructs.
 * All resource logic and outputs are contained within the L3 constructs.
 */
export class AgentCoreStack extends Stack {
  /** The AgentCore application containing all agent environments */
  public readonly application: AgentCoreApplication;

  /** The runtime ARN for the TAC agent (for cross-stack reference) */
  public readonly runtimeArn: string;

  constructor(scope: Construct, id: string, props: AgentCoreStackProps) {
    super(scope, id, props);

    const { spec, twilioSecretArn } = props;

    // Import the secret from ARN
    const twilioSecret = secretsmanager.Secret.fromSecretCompleteArn(
      this,
      'TwilioSecret',
      twilioSecretArn
    );

    // Enhanced spec with secret ARN as environment variable
    const enhancedSpec = {
      ...spec,
      runtimes: spec.runtimes.map(runtime => ({
        ...runtime,
        envVars: [
          ...(runtime.envVars || []),
          { name: 'TWILIO_SECRET_ARN', value: twilioSecretArn },
        ],
      })),
    };

    // Create AgentCoreApplication with enhanced spec
    this.application = new AgentCoreApplication(this, 'Application', {
      spec: enhancedSpec,
    });

    // Get the runtime ARN from the first (and only) runtime
    const runtimeName = spec.runtimes[0]?.name;
    if (!runtimeName) {
      throw new Error('No runtimes defined in agentcore.json');
    }

    const environment = this.application.environments.get(runtimeName);
    if (!environment) {
      throw new Error(`Runtime environment ${runtimeName} not found`);
    }

    this.runtimeArn = environment.runtime.runtimeArn;

    // Grant runtime permission to read the secret
    const runtimeRole = environment.runtime.role;
    twilioSecret.grantRead(runtimeRole);

    // Stack-level outputs
    new CfnOutput(this, 'StackNameOutput', {
      description: 'Name of the CloudFormation Stack',
      value: this.stackName,
    });

    new CfnOutput(this, 'AgentCoreRuntimeArn', {
      description: 'AgentCore Runtime ARN',
      value: this.runtimeArn,
      exportName: 'TacAgentCoreRuntimeArn',  // Export for cross-stack reference
    });
  }
}
