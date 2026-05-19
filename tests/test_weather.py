from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.models.weather import WeatherRequest


@pytest.mark.asyncio
async def test_get_weather_success_and_caching(client, db_session):
    """Тест кэширования через новый сервис"""

    now = datetime.now(timezone.utc)

    weather_request = WeatherRequest(
        city="Paris",
        temperature=18.5,
        description="переменная облачность",
        humidity=65,
        units="C",
        is_cached=False,
        timestamp=now,
    )

    cached_request = WeatherRequest(
        city="Paris",
        temperature=18.5,
        description="переменная облачность",
        humidity=65,
        units="C",
        is_cached=True,
        timestamp=now,
    )

    with patch("app.api.v1.weather.cache_service") as mock_service:
        mock_service.get_or_fetch = AsyncMock(return_value=weather_request)

        response1 = client.get("/api/v1/weather?city=Paris&units=celsius")
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["is_cached"] is False
        assert mock_service.get_or_fetch.call_count == 1

        mock_service.get_or_fetch = AsyncMock(return_value=cached_request)

        response2 = client.get("/api/v1/weather?city=Paris&units=celsius")
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["is_cached"] is True


def test_get_weather_city_not_found(client):
    """Тест: город не найден"""
    with patch("app.api.v1.weather.cache_service") as mock_service:
        mock_service.get_or_fetch = AsyncMock(return_value=None)

        response = client.get("/api/v1/weather?city=NonExistentCity&units=celsius")
        assert response.status_code == 404
        assert "Город не найден" in response.json()["detail"]


def test_get_weather_different_units_cached_separately(client):
    """Тест: кэш для разных единиц измерения независим"""

    now = datetime.now(timezone.utc)

    with patch("app.api.v1.weather.cache_service") as mock_service:
        celsius_request = WeatherRequest(
            city="Paris",
            temperature=18.5,
            description="ясно",
            humidity=65,
            units="C",
            is_cached=False,
            timestamp=now,
        )
        fahrenheit_request = WeatherRequest(
            city="Paris",
            temperature=65.3,
            description="ясно",
            humidity=65,
            units="F",
            is_cached=False,
            timestamp=now,
        )

        mock_service.get_or_fetch = AsyncMock()
        mock_service.get_or_fetch.side_effect = [celsius_request, fahrenheit_request]

        response_c = client.get("/api/v1/weather?city=Paris&units=celsius")
        assert response_c.status_code == 200
        assert response_c.json()["units"] == "C"

        response_f = client.get("/api/v1/weather?city=Paris&units=fahrenheit")
        assert response_f.status_code == 200
        assert response_f.json()["units"] == "F"

        assert mock_service.get_or_fetch.call_count == 2


def test_get_weather_invalid_city_validation(client):
    """Тест валидации города - специальные символы"""

    response = client.get("/api/v1/weather?city=London123&units=celsius")
    assert response.status_code == 422

    with patch("app.api.v1.weather.cache_service") as mock_service:
        now = datetime.now(timezone.utc)
        mock_request = WeatherRequest(
            city="New-York",
            temperature=15.0,
            description="облачно",
            humidity=70,
            units="C",
            is_cached=False,
            timestamp=now,
        )
        mock_service.get_or_fetch = AsyncMock(return_value=mock_request)

        response = client.get("/api/v1/weather?city=New-York&units=celsius")
        assert response.status_code == 200

    with patch("app.api.v1.weather.cache_service") as mock_service:
        now = datetime.now(timezone.utc)
        mock_request = WeatherRequest(
            city="Saint Petersburg",
            temperature=15.0,
            description="облачно",
            humidity=70,
            units="C",
            is_cached=False,
            timestamp=now,
        )
        mock_service.get_or_fetch = AsyncMock(return_value=mock_request)

        response = client.get("/api/v1/weather?city=Saint%20Petersburg&units=celsius")
        assert response.status_code == 200

def test_get_weather_redis_connection_error(client, monkeypatch):
    """Тест ошибки подключения к Redis"""
    from app.services.weather_cache import WeatherCacheService

    class BrokenRedis:
        def get(self, *args, **kwargs):
            raise Exception("Redis connection failed")

        def setex(self, *args, **kwargs):
            raise Exception("Redis connection failed")

    broken_service = WeatherCacheService(redis_client=BrokenRedis())

    with patch("app.api.v1.weather.cache_service", broken_service):
        with patch.object(broken_service.api_client, 'get_current_weather') as mock_api:
            mock_api.return_value = {
                "name": "Moscow",
                "main": {"temp": 20.5, "humidity": 65},
                "weather": [{"description": "ясно"}]
            }

            response = client.get("/api/v1/weather?city=Moscow&units=celsius")
            assert response.status_code == 200
            data = response.json()
            assert data["city"] == "Moscow"


def test_get_weather_redis_get_error(client):
    """Тест ошибки Redis при GET операции"""
    from app.services.weather_cache import WeatherCacheService

    class RedisGetError:
        def get(self, *args, **kwargs):
            raise Exception("Redis GET error")

        def setex(self, *args, **kwargs):
            pass

    broken_service = WeatherCacheService(redis_client=RedisGetError())

    with patch("app.api.v1.weather.cache_service", broken_service):
        with patch.object(broken_service.api_client, 'get_current_weather') as mock_api:
            mock_api.return_value = {
                "name": "Berlin",
                "main": {"temp": 22.0, "humidity": 70},
                "weather": [{"description": "облачно"}]
            }

            response = client.get("/api/v1/weather?city=Berlin&units=celsius")
            assert response.status_code == 200
            data = response.json()
            assert data["city"] == "Berlin"
            assert data["is_cached"] is False