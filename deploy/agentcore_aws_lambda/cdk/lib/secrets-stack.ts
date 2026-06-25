import * as cdk from 'aws-cdk-lib';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

export class SecretsStack extends cdk.Stack {
  public readonly twilioSecret: secretsmanager.ISecret;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create secret with placeholder values
    // Real values populated via 'make secret-update' after deployment
    this.twilioSecret = new secretsmanager.Secret(this, 'TwilioCredentials', {
      secretName: 'tac/twilio-credentials',
      description: 'Twilio credentials and configuration for TAC (auto-updated by make deploy)',
      secretObjectValue: {
        TWILIO_ACCOUNT_SID: cdk.SecretValue.unsafePlainText('PLACEHOLDER'),
        TWILIO_AUTH_TOKEN: cdk.SecretValue.unsafePlainText('PLACEHOLDER'),
        TWILIO_API_KEY: cdk.SecretValue.unsafePlainText('PLACEHOLDER'),
        TWILIO_API_SECRET: cdk.SecretValue.unsafePlainText('PLACEHOLDER'),
        TWILIO_PHONE_NUMBER: cdk.SecretValue.unsafePlainText('PLACEHOLDER'),
        TWILIO_CONVERSATION_CONFIGURATION_ID: cdk.SecretValue.unsafePlainText('PLACEHOLDER'),
      },
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
