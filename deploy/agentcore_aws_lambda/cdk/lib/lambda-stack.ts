import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';

export interface LambdaStackProps extends cdk.StackProps {
  agentCoreRuntimeArn: string;
  twilioConversationConfigurationId: string;
  twilioAuthToken: string;
}

export class LambdaStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: LambdaStackProps) {
    super(scope, id, props);

    // Lambda function with Python dependencies
    const lambdaFunction = new PythonFunction(this, 'TacAgentcoreLambda', {
      entry: '../lambda',  // Reference lambda directory
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'lambda_handler',
      index: 'index.py',
      timeout: cdk.Duration.seconds(30),
      memorySize: 1024,
      environment: {
        AGENTCORE_RUNTIME_ARN: props.agentCoreRuntimeArn,
        TWILIO_CONVERSATION_CONFIGURATION_ID: props.twilioConversationConfigurationId,
        TWILIO_AUTH_TOKEN: props.twilioAuthToken,
      },
    });

    // Grant permissions to invoke AgentCore
    // InvokeAgentRuntime: For SMS HTTP invocations
    // InvokeAgentRuntimeWithWebSocketStream: For Voice WebSocket connections
    // Scoped to the specific AgentCore runtime for least-privilege access
    lambdaFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: [
        'bedrock-agentcore:InvokeAgentRuntime',
        'bedrock-agentcore:InvokeAgentRuntimeWithWebSocketStream',
      ],
      resources: [
        props.agentCoreRuntimeArn,
        `${props.agentCoreRuntimeArn}/*`,
      ],
    }));

    // Add Function URL (public)
    // Signature validation handled in Lambda handler
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
