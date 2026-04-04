"""Unit tests for the Jira service Lambda handler wiring."""

import importlib
import sys
import types
from typing import Any

import pytest

from jira_service.main import app as main_app


def test_handler_initializes_mangum_with_expected_parameters(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify handler initializes Mangum with FastAPI app and config."""
    created: dict[str, object] = {}

    def fake_mangum(
        app: object,
        lifespan: str | None = None,
        api_gateway_base_path: str | None = None,
    ) -> types.SimpleNamespace:
        created["app"] = app
        created["lifespan"] = lifespan
        created["api_gateway_base_path"] = api_gateway_base_path
        return types.SimpleNamespace(
            app=app,
            lifespan=lifespan,
            api_gateway_base_path=api_gateway_base_path,
        )

    # Create fake mangum with the fake_mangum function.
    fake_mangum_module = types.ModuleType("mangum")
    fake_mangum_module.Mangum = fake_mangum  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "mangum", fake_mangum_module)
    sys.modules.pop("jira_service.handler", None)

    _module: Any = importlib.import_module("jira_service.handler")

    assert created["app"] is main_app
    assert created["lifespan"] == "off"
    assert created["api_gateway_base_path"] == "/default-deployment"
