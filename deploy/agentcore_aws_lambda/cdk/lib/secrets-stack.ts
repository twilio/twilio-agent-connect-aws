import * as cdk from 'aws-cdk-lib';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

export interface SecretsStackProps extends cdk.StackProps {
  twilioAccountSid: string;
  twilioAuthToken: string;
  twilioApiKey: string;
  twilioApiSecret: string;
  twilioPhoneNumber: string;
  twilioConversationConfigurationId: string;
}

/**
 * CDK Stack for managing Twilio credentials in AWS Secrets Manager.
 *
 * This stack creates a secret containing all Twilio credentials needed for
 * TAC AgentCore deployment. The secret is referenced by both Lambda and AgentCore stacks.
 */
export class SecretsStack extends cdk.Stack {
  /** The secret containing Twilio credentials */
  public readonly twilioSecret: secretsmanager.ISecret;

  constructor(scope: Construct, id: string, props: SecretsStackProps) {
    super(scope, id, props);

    // Create secret with all Twilio credentials
    // Using secretObjectValue allows CDK to update the secret when .env changes
    // RemovalPolicy.RETAIN prevents accidental deletion when stack is destroyed
    //
    // SECURITY NOTE: unsafePlainText() means these values will appear in:
    // - CloudFormation template (cdk.out/ directory)
    // - CloudFormation console (visible to users with console access)
    // - cdk diff output
    // This is acceptable for local development deployments, but for production
    // environments, consider creating the secret manually via AWS CLI instead:
    //   aws secretsmanager create-secret --name tac/twilio-credentials \
    //     --secret-string '{"TWILIO_ACCOUNT_SID":"...","TWILIO_AUTH_TOKEN":"...",...}'
    // Then import it with: Secret.fromSecretNameV2(this, 'Secret', 'tac/twilio-credentials')
    this.twilioSecret = new secretsmanager.Secret(this, 'TwilioCredentials', {
      secretName: 'tac/twilio-credentials',
      description: 'Twilio credentials for TAC AgentCore deployment',
      secretObjectValue: {
        TWILIO_ACCOUNT_SID: cdk.SecretValue.unsafePlainText(props.twilioAccountSid),
        TWILIO_AUTH_TOKEN: cdk.SecretValue.unsafePlainText(props.twilioAuthToken),
        TWILIO_API_KEY: cdk.SecretValue.unsafePlainText(props.twilioApiKey),
        TWILIO_API_SECRET: cdk.SecretValue.unsafePlainText(props.twilioApiSecret),
        TWILIO_PHONE_NUMBER: cdk.SecretValue.unsafePlainText(props.twilioPhoneNumber),
        TWILIO_CONVERSATION_CONFIGURATION_ID: cdk.SecretValue.unsafePlainText(
          props.twilioConversationConfigurationId
        ),
      },
      removalPolicy: cdk.RemovalPolicy.RETAIN, // Keep secret when stack is deleted
    });

    // Outputs
    new cdk.CfnOutput(this, 'SecretArn', {
      value: this.twilioSecret.secretArn,
      description: 'ARN of Twilio credentials secret',
      exportName: 'TacTwilioSecretArn',
    });

    new cdk.CfnOutput(this, 'SecretName', {
      value: this.twilioSecret.secretName,
      description: 'Name of Twilio credentials secret',
    });
  }
}
