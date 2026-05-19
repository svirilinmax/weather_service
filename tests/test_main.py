from fastapi.testclient import TestClient

from app.main import app


def test_read_root():
    """Тест корневого эндпоинта"""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Weather Service" in response.json()["message"]


def test_weather_page():
    """Тест HTML страницы погоды"""
    client = TestClient(app)
    response = client.get("/weather")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_docs_page():
    """Тест Swagger документации"""
    client = TestClient(app)
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_json():
    """Тест OpenAPI спецификации"""
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "paths" in data
    assert "/api/v1/weather" in data["paths"]


def test_read_root_with_debug():
    """Тест корневого эндпоинта"""
    from app.config import settings

    original_debug = settings.DEBUG
    try:
        settings.DEBUG = True
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "Weather Service" in response.json()["message"]
    finally:
        settings.DEBUG = original_debug


def test_root_endpoint_json_response():
    """Тест JSON ответа корневого эндпоинта"""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    data = response.json()
    assert "message" in data
    assert "Weather Service" in data["message"]
