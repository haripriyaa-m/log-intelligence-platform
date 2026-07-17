def test_import_api():
    """Verify the API module imports without errors."""
    from api.main import app
    assert app is not None

def test_health_endpoint_exists():
    """Verify the health endpoint is registered."""
    from api.main import app
    routes = [r.path for r in app.routes]
    assert "/health" in routes

def test_services_endpoint_exists():
    from api.main import app
    routes = [r.path for r in app.routes]
    assert "/services/" in routes