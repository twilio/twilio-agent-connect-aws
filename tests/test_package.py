"""Tests for package structure and imports."""

from __future__ import annotations

import pytest


class TestPackageImports:
    """Test suite for package imports and structure."""

    def test_package_version(self) -> None:
        """Test that package version is accessible."""
        import tac_aws

        assert hasattr(tac_aws, "__version__")
        assert isinstance(tac_aws.__version__, str)

    def test_strands_connector_import(self) -> None:
        """Test that StrandsConnector can be imported from package root."""
        from tac_aws import StrandsConnector

        assert StrandsConnector is not None

    def test_strands_connector_direct_import(self) -> None:
        """Test that StrandsConnector can be imported from connectors module."""
        from tac_aws.connectors import StrandsConnector

        assert StrandsConnector is not None

    def test_memory_tool_import(self) -> None:
        """Test that create_memory_tool can be imported."""
        from tac_aws.tools import create_memory_tool

        assert create_memory_tool is not None
        assert callable(create_memory_tool)

    def test_memory_tool_strands_import(self) -> None:
        """Test that create_memory_tool can be imported from strands submodule."""
        from tac_aws.tools.strands import create_memory_tool

        assert create_memory_tool is not None
        assert callable(create_memory_tool)

    def test_package_all_exports(self) -> None:
        """Test that __all__ exports are correct."""
        import tac_aws

        # Check __all__ contains expected exports
        assert hasattr(tac_aws, "__all__")
        assert "StrandsConnector" in tac_aws.__all__
        assert "__version__" in tac_aws.__all__

    def test_connectors_module_exports(self) -> None:
        """Test that connectors module exports are correct."""
        import tac_aws.connectors as connectors

        assert hasattr(connectors, "__all__")
        assert "StrandsConnector" in connectors.__all__

    def test_tools_module_exports(self) -> None:
        """Test that tools module exports are correct."""
        import tac_aws.tools as tools

        assert hasattr(tools, "__all__")
        assert "create_memory_tool" in tools.__all__

    def test_no_legacy_adapter_imports(self) -> None:
        """Test that old adapter/handler modules are removed."""
        with pytest.raises(ImportError):
            from tac_aws.adapters import BaseAgentAdapter  # noqa: F401

        with pytest.raises(ImportError):
            from tac_aws.adapters import StrandsAdapter  # noqa: F401

        with pytest.raises(ImportError):
            from tac_aws.handlers import OmniChannelHandler  # noqa: F401

    def test_strands_connector_has_required_methods(self) -> None:
        """Test that StrandsConnector has required public methods."""
        from tac_aws.connectors import StrandsConnector

        # Check for required methods
        assert hasattr(StrandsConnector, "__init__")
        assert hasattr(StrandsConnector, "_handle_message")
        assert hasattr(StrandsConnector, "_handle_conversation_ended")

    def test_create_memory_tool_signature(self) -> None:
        """Test that create_memory_tool has expected signature."""
        import inspect

        from tac_aws.tools import create_memory_tool

        sig = inspect.signature(create_memory_tool)

        # Should have one parameter: memory_client
        assert len(sig.parameters) == 1
        assert "memory_client" in sig.parameters

    def test_strands_connector_agent_factory_signature(self) -> None:
        """Test that agent_factory receives ConversationSession parameter."""
        import inspect

        from tac_aws.connectors import StrandsConnector

        # Check __init__ signature
        sig = inspect.signature(StrandsConnector.__init__)
        assert "agent_factory" in sig.parameters

        # The type hint should indicate Callable[[ConversationSession], Agent]
        # We can't easily check the full type at runtime, but we can verify the parameter exists
        agent_factory_param = sig.parameters["agent_factory"]
        assert agent_factory_param is not None
