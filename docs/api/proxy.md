# Proxy

AWS Lambda proxy handlers for Twilio webhooks. Requires the `agentcore` extra.

<!-- Documented per-module rather than via `::: tac_aws.proxy` because the
     package gates these imports behind try/except for optional dependencies,
     which griffe cannot resolve statically. -->

## AgentCore Lambda Proxy

::: tac_aws.proxy.agentcore_lambda
    options:
      show_submodules: false

## Signature Validation

::: tac_aws.proxy.validation
    options:
      show_submodules: false
