import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';

export interface LambdaStackProps extends cdk.StackProps {
  agentCoreRuntimeArn: string;
  twilioConversationConfigurationId: string;
}

export class LambdaStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: LambdaStackProps) {
    super(scope, id, props);

    // Lambda function with Python dependencies
    const lambdaFunction = new PythonFunction(this, 'TacAgentcoreLambda', {
      entry: '../app',  // Reference app directory
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'lambda_handler',
      index: 'index.py',
      timeout: cdk.Duration.seconds(30),
      memorySize: 1024,
      environment: {
        AGENTCORE_RUNTIME_ARN: props.agentCoreRuntimeArn,
        TWILIO_CONVERSATION_CONFIGURATION_ID: props.twilioConversationConfigurationId,
      },
    });

    // Grant permissions to invoke AgentCore
    lambdaFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['bedrock-agentcore:*'],
      resources: [
        `arn:aws:bedrock-agentcore:${this.region}:${this.account}:runtime/*`,
      ],
    }));

    // Add Function URL (public)
    const functionUrl = lambdaFunction.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.NONE,
    });

    // Outputs
    new cdk.CfnOutput(this, 'VoiceWebhookUrl', {
      value: `${functionUrl.url}twiml`,
      description: 'Twilio Voice Webhook URL',
    });

    new cdk.CfnOutput(this, 'ConversationWebhookUrl', {
      value: `${functionUrl.url}webhook`,
      description: 'Twilio Conversation Webhook URL',
    });

    new cdk.CfnOutput(this, 'FunctionArn', {
      value: lambdaFunction.functionArn,
      description: 'Lambda Function ARN',
    });
  }
}
