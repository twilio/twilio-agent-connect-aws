import * as cdk from 'aws-cdk-lib';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

export class SecretsStack extends cdk.Stack {
  public readonly twilioSecret: secretsmanager.ISecret;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Secret with placeholder value (populated by 'make secret-update')
    // DESTROY policy allows clean redeploy. Credentials are in .env and can be restored.
    this.twilioSecret = new secretsmanager.Secret(this, 'TwilioCredentials', {
      secretName: 'tac/twilio-credentials',
      description: 'Twilio credentials for TAC',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
  }
}
