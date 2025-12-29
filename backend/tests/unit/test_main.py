from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.main import CORS_ORIGINS, app


def _get_cors_middleware():
    for middleware in app.user_middleware:
        if middleware.cls is CORSMiddleware:
            return middleware
    raise AssertionError("CORSMiddleware not configured")


def test_lifespan_hooks_toggle_state():
    with TestClient(app):
        assert app.state.lifespan_started is True
    assert app.state.lifespan_shutdown is True


def test_router_mounts_api_prefix():
    paths = {route.path for route in app.router.routes}
    assert "/api/healthz" in paths


def test_cors_defaults():
    middleware = _get_cors_middleware()
    assert middleware.kwargs["allow_origins"] == CORS_ORIGINS
    assert middleware.kwargs["allow_methods"] == ["*"]
    assert middleware.kwargs["allow_headers"] == ["*"]
