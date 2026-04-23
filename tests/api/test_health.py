from app.main import create_app


def test_health_returns_ok_payload() -> None:
    app = create_app()
    route = next(route for route in app.router.routes if getattr(route, "path", None) == "/health")

    assert route.endpoint() == {"status": "ok"}
