# Server

Server utilities for running TAC on AWS. Requires the `server` extra; the
AgentCore app additionally requires the `agentcore` extra.

<!-- Documented per-module rather than via `::: tac_aws.server` because the
     package gates these imports behind try/except for optional dependencies,
     which griffe cannot resolve statically. -->

## FastAPI Server

::: tac_aws.server.fastapi_server
    options:
      show_submodules: false

## AgentCore App

::: tac_aws.server.agentcore_app
    options:
      show_submodules: false
