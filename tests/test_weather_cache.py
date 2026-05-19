import json
from unittest.mock import AsyncMock, MagicMock

import fakeredis
import pytest
from sqlalchemy.orm import Session

from app.models.weather import WeatherRequest
from app.schemas.enums import TemperatureUnit
from app.services.weather_cache import WeatherCacheService, logger


class TestWeatherCacheService:
    """Тесты для WeatherCacheService"""

    @pytest.fixture
    def cache_service(self):
        """Создает сервис с фейковым Redis"""
        fake_redis = fakeredis.FakeRedis(decode_responses=True)
        service = WeatherCacheService(redis_client=fake_redis)
        service.api_client.get_current_weather = AsyncMock()
        return service

    @pytest.fixture
    def db_session_mock(self):
        """Мок для сессии БД"""
        session = MagicMock(spec=Session)
        session.add = MagicMock()
        session.commit = MagicMock()
        session.refresh = MagicMock()
        return session

    def test_make_cache_key(self, cache_service):
        """Тест генерации ключа для Redis"""
        key = cache_service._make_cache_key("Moscow", TemperatureUnit.CELSIUS)
        assert key == "weather:moscow:C"

        key = cache_service._make_cache_key("  New York  ", TemperatureUnit.FAHRENHEIT)
        assert key == "weather:new york:F"

    @pytest.mark.asyncio
    async def test_get_from_redis_success(self, cache_service):
        """Тест успешного получения данных из Redis"""
        cache_key = "weather:paris:C"
        test_data = {"city": "Paris", "temperature": 18.5}

        await cache_service._save_to_redis(cache_key, test_data)

        result = await cache_service._get_from_redis(cache_key)
        assert result == test_data

    @pytest.mark.asyncio
    async def test_get_from_redis_not_found(self, cache_service):
        """Тест: данных нет в Redis"""
        result = await cache_service._get_from_redis("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_from_redis_connection_error(self, cache_service):
        """Тест ошибки подключения к Redis"""
        mock_redis = MagicMock()
        mock_redis.get.side_effect = Exception("Connection error")
        cache_service.redis_client = mock_redis

        result = await cache_service._get_from_redis("some_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_save_to_redis_success(self, cache_service):
        """Тест успешного сохранения в Redis"""
        cache_key = "weather:london:C"
        test_data = {"city": "London", "temperature": 15.5}

        await cache_service._save_to_redis(cache_key, test_data)

        result = cache_service.redis_client.get(cache_key)
        assert result is not None
        assert json.loads(result) == test_data

    @pytest.mark.asyncio
    async def test_save_to_redis_connection_error(self, cache_service):
        """Тест ошибки при сохранении в Redis"""
        mock_redis = MagicMock()
        mock_redis.setex.side_effect = Exception("Connection error")
        cache_service.redis_client = mock_redis

        await cache_service._save_to_redis("key", {"data": "test"})

    def test_save_to_db_success(self, cache_service, db_session_mock):
        """Тест успешного сохранения в БД"""
        weather = cache_service._save_to_db(
            db=db_session_mock,
            city="Moscow",
            temperature=20.5,
            description="солнечно",
            humidity=65,
            units="C",
            is_cached=False
        )

        assert weather.city == "Moscow"
        assert weather.temperature == 20.5
        assert weather.description == "солнечно"
        assert weather.units == "C"
        assert weather.is_cached is False
        db_session_mock.add.assert_called_once()
        db_session_mock.commit.assert_called_once()
        db_session_mock.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_fetch_from_cache(self, cache_service, db_session_mock):
        """Тест: данные берутся из кэша"""
        cache_key = "weather:moscow:C"
        cached_data = {
            "city": "Moscow",
            "temperature": 20.5,
            "description": "солнечно",
            "humidity": 65
        }

        await cache_service._save_to_redis(cache_key, cached_data)

        result = await cache_service.get_or_fetch(
            db_session_mock, "Moscow", TemperatureUnit.CELSIUS
        )

        assert result.is_cached is True
        assert result.city == "Moscow"
        assert result.temperature == 20.5
        cache_service.api_client.get_current_weather.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_fetch_from_api(self, cache_service, db_session_mock):
        """Тест: данных нет в кэше - запрос в API"""
        mock_api_response = {
            "name": "Berlin",
            "main": {"temp": 22.0, "humidity": 70},
            "weather": [{"description": "облачно"}]
        }
        cache_service.api_client.get_current_weather = AsyncMock(return_value=mock_api_response)

        result = await cache_service.get_or_fetch(
            db_session_mock, "Berlin", TemperatureUnit.CELSIUS
        )

        assert result.is_cached is False
        assert result.city == "Berlin"
        assert result.temperature == 22.0
        cache_service.api_client.get_current_weather.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_fetch_api_returns_none(self, cache_service, db_session_mock):
        """Тест: API вернул None (город не найден)"""
        cache_service.api_client.get_current_weather = AsyncMock(return_value=None)

        result = await cache_service.get_or_fetch(
            db_session_mock, "NonExistent", TemperatureUnit.CELSIUS
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_or_fetch_api_parse_error(self, cache_service, db_session_mock):
        """Тест: ошибка парсинга ответа API"""
        mock_api_response = {"invalid": "response"}
        cache_service.api_client.get_current_weather = AsyncMock(return_value=mock_api_response)

        with pytest.raises(Exception):
            await cache_service.get_or_fetch(
                db_session_mock, "Berlin", TemperatureUnit.CELSIUS
            )

    @pytest.mark.asyncio
    async def test_get_or_fetch_redis_error_on_save(self, db_session_mock):
        """Тест: ошибка Redis при сохранении не должна прерывать работу"""
        fake_redis = fakeredis.FakeRedis(decode_responses=True)

        service = WeatherCacheService(redis_client=fake_redis)
        mock_api_response = {
            "name": "Tokyo",
            "main": {"temp": 25.0, "humidity": 60},
            "weather": [{"description": "солнечно"}]
        }
        service.api_client.get_current_weather = AsyncMock(return_value=mock_api_response)

        original_save = service._save_to_redis

        error_logged = False

        async def broken_save(*args, **kwargs):
            nonlocal error_logged
            error_logged = True
            logger.error("Redis save error")

        service._save_to_redis = broken_save

        result = await service.get_or_fetch(
            db_session_mock, "Tokyo", TemperatureUnit.CELSIUS
        )

        assert result is not None
        assert result.city == "Tokyo"
        assert result.temperature == 25.0
        assert error_logged is True