import * as cdk from 'aws-cdk-lib';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

export class SecretsStack extends cdk.Stack {
  public readonly twilioSecret: secretsmanager.ISecret;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create secret resource with placeholder value (overwritten by 'make secret-update')
    this.twilioSecret = new secretsmanager.Secret(this, 'TwilioCredentials', {
      secretName: 'tac/twilio-credentials',
      description: 'Twilio credentials and configuration for TAC',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Output secret ARN for cross-stack references
    new cdk.CfnOutput(this, 'SecretArn', {
      value: this.twilioSecret.secretArn,
      description: 'Twilio credentials secret ARN',
    });

    new cdk.CfnOutput(this, 'SecretName', {
      value: this.twilioSecret.secretName,
      description: 'Twilio credentials secret name',
    });
  }
}
