import importlib
import sys
import types

from main import app as main_app


def test_handler_initializes_mangum_with_expected_parameters(monkeypatch):
    """Verify handler initializes Mangum with FastAPI app and config."""
    created = {}

    def fake_mangum(app, lifespan=None, api_gateway_base_path=None):
        created["app"] = app
        created["lifespan"] = lifespan
        created["api_gateway_base_path"] = api_gateway_base_path
        return types.SimpleNamespace(
            app=app,
            lifespan=lifespan,
            api_gateway_base_path=api_gateway_base_path,
        )
    #create fake mangum with the fake_mangum function
    fake_mangum_module = types.ModuleType("mangum")
    setattr(fake_mangum_module, "Mangum", fake_mangum)

    monkeypatch.setitem(sys.modules, "mangum", fake_mangum_module)
    sys.modules.pop("handler", None)

    _ = importlib.import_module("handler")

    assert created["app"] is main_app
    assert created["lifespan"] == "off"
