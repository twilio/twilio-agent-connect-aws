import * as cdk from 'aws-cdk-lib';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

export class SecretsStack extends cdk.Stack {
  public readonly twilioSecret: secretsmanager.ISecret;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create secret resource with placeholder value (overwritten by 'make secret-update')
    // RETAIN prevents accidental credential deletion when stack is deleted/replaced.
    // Note: If you delete the stack and redeploy, you must first manually delete the secret:
    //   aws secretsmanager delete-secret --secret-id tac/twilio-credentials --region <region>
    this.twilioSecret = new secretsmanager.Secret(this, 'TwilioCredentials', {
      secretName: 'tac/twilio-credentials',
      description: 'Twilio credentials and configuration for TAC',
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });
  }
}
