from fastapi.testclient import TestClient
from app.main import app


def test_logging_middleware_error():
    """Тест логирования ошибок"""
    client = TestClient(app)

    response = client.get("/non-existent-endpoint")
    assert response.status_code == 404