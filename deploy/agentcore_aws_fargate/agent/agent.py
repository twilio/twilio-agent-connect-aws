from strands import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp

agent = Agent(model="amazon.nova-pro-v1:0")
app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload):
    """Process user input and return a response"""
    user_message = payload.get("prompt", "Hello")
    response = agent(user_message)
    return str(response)


if __name__ == "__main__":
    app.run()
