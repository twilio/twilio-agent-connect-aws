# Connectors

Connectors combine AWS agent runtime integration with TAC channel management.

::: tac_aws.connectors
    options:
      show_submodules: false

## Channels

Every connector builds the same channel set — Voice, SMS, RCS, WhatsApp, and
Chat — and routes responses through it. `connector.channels` exposes it.

::: tac_aws.connectors.channels
    options:
      show_submodules: false

## AgentCore Runtime Configuration

Configuration objects for [`BedrockAgentCoreConnector`][tac_aws.connectors.BedrockAgentCoreConnector].

::: tac_aws.connectors.bedrock_agentcore.config
    options:
      show_submodules: false
