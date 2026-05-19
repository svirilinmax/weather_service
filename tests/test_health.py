from unittest.mock import patch

from sqlalchemy.exc import SQLAlchemyError


def test_health_check_db_error(client, monkeypatch):
    """Тест ошибки подключения к БД"""

    with patch(
        "sqlalchemy.engine.base.Connection.execute",
        side_effect=SQLAlchemyError("DB error"),
    ):
        response = client.get("/api/v1/health")
        assert response.status_code == 503
        data = response.json()
        assert data["database"] == "disconnected"
        assert data["status"] == "unhealthy"


def test_health_check_external_api_error(client, monkeypatch):
    """Тест недоступности внешнего API"""
    from app.api.v1 import health

    async def mock_external_unreachable():
        return False, 500.0

    monkeypatch.setattr(health, "check_external_api", mock_external_unreachable)

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["external_api"] == "unreachable"
    assert data["status"] == "degraded"
