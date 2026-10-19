from app.main import create_app


def test_web_routes_are_registered() -> None:
    app = create_app()
    paths = {route.path for route in app.router.routes if hasattr(route, "path")}

    assert "/" in paths
    assert "/iocs" in paths
    assert "/iocs/{ioc_id}" in paths
    assert "/imports" in paths
    assert "/exports" in paths
    assert "/health" in paths
