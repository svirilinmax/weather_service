from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch


def test_logging_middleware_error():
    """Тест логирования ошибок (404)"""
    client = TestClient(app)

    response = client.get("/non-existent-endpoint")
    assert response.status_code == 404


def test_logging_middleware_success():
    """Тест успешного запроса с логированием"""
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200


def test_logging_middleware_exception_handling():
    """Тест обработки исключений в middleware"""
    client = TestClient(app, raise_server_exceptions=False)

    @app.get("/test-exception-endpoint")
    async def raise_error():
        raise ValueError("Test exception from endpoint")

    with patch("app.middlewares.logging_middleware.logger") as mock_logger:
        response = client.get("/test-exception-endpoint")
        assert response.status_code == 500
        mock_logger.error.assert_called()

    app.routes[:] = [r for r in app.routes if r.path != "/test-exception-endpoint"]
