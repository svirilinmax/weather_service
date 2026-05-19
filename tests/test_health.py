from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError


def test_health_check_db_error(client, monkeypatch):
    """Тест ошибки подключения к БД"""
    from app.api.v1 import health

    async def mock_check_external():
        return True, 100.0

    monkeypatch.setattr(health, "check_external_api", mock_check_external)

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
    assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_check_external_api_success(monkeypatch):
    """Тест проверки внешнего API - успех"""
    from app.api.v1 import health

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        ok, duration = await health.check_external_api()
        assert ok is True
        assert duration > 0


@pytest.mark.asyncio
async def test_check_external_api_timeout(monkeypatch):
    """Тест проверки внешнего API - таймаут"""
    from app.api.v1 import health

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = Exception("Timeout")

        ok, duration = await health.check_external_api()
        assert ok is False
        assert duration > 0


def test_health_check_all_ok(client, monkeypatch):
    """Тест: всё работает"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
