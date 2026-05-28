import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export class TacAgentcoreTwilioFunctionStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create IAM User for Twilio Functions
    const twilioFunctionUser = new iam.User(this, 'TacAgentcoreTwilioFunctionUser', {
      userName: 'tac-agentcore-twilio-function-user',
    });

    // Add policy for AgentCore access
    twilioFunctionUser.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['bedrock-agentcore:*'],
      resources: [
        `arn:aws:bedrock-agentcore:${this.region}:${this.account}:runtime/*`,
      ],
    }));

    // Create access key for the user
    const accessKey = new iam.CfnAccessKey(this, 'TacAgentcoreTwilioFunctionAccessKey', {
      userName: twilioFunctionUser.userName,
    });

    // Outputs
    new cdk.CfnOutput(this, 'UserName', {
      value: twilioFunctionUser.userName,
      description: 'IAM User Name',
    });

    new cdk.CfnOutput(this, 'AccessKeyId', {
      value: accessKey.ref,
      description: 'Access Key ID (use in .env as AWS_ACCESS_KEY_ID)',
    });

    new cdk.CfnOutput(this, 'SecretAccessKey', {
      value: accessKey.attrSecretAccessKey,
      description: 'Secret Access Key (use in .env as AWS_SECRET_ACCESS_KEY) - SAVE THIS NOW!',
    });

    new cdk.CfnOutput(this, 'Warning', {
      value: 'The Secret Access Key is only visible once. Copy it immediately to your .env file.',
      description: 'Security Notice',
    });
  }
}
