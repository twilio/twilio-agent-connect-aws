"""Single source of truth for the aws-twilio-agent-connect package version.

Kept in a leaf module so it can be imported from connectors without pulling in
``tac_aws/__init__.py`` (which would cause a circular import).
"""

from importlib.metadata import version

__version__ = version("aws-twilio-agent-connect")
