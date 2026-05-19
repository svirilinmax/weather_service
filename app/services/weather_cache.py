import json
import logging
from typing import Optional

import redis
from sqlalchemy.orm import Session

from app.config import settings
from app.models.weather import WeatherRequest
from app.schemas.enums import TemperatureUnit
from app.services.weather_api import WeatherAPIClient

logger = logging.getLogger("weather_logger")


class WeatherCacheService:
    def __init__(self, redis_client=None):
        """Позволяет передать Redis клиент для тестирования"""
        self.redis_client = redis_client or redis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
        self.api_client = WeatherAPIClient()

    def _make_cache_key(self, city: str, units: TemperatureUnit) -> str:
        """Генерирует ключ для Redis"""
        return f"weather:{city.lower().strip()}:{units.to_db_letter()}"  # noqa 231

    async def _get_from_redis(self, key: str) -> Optional[dict]:
        """Получает данные из кэша"""
        try:
            cached_raw = self.redis_client.get(key)
            if cached_raw:
                return json.loads(cached_raw)
        except redis.ConnectionError as e:
            logger.error(f"action='redis_error' error='{e}' key='{key}'")
        except Exception as e:
            logger.error(f"action='redis_unexpected_error' error='{e}' key='{key}'")
        return None

    async def _save_to_redis(self, key: str, data: dict) -> None:
        """Сохраняет данные в кэш"""
        try:
            self.redis_client.setex(
                key, settings.WEATHER_CACHE_TTL_SECONDS, json.dumps(data)
            )
            logger.info(
                f"action='cache_set' key='{key}' "
                f"ttl={settings.WEATHER_CACHE_TTL_SECONDS}"
            )
        except redis.ConnectionError as e:
            logger.error(f"action='redis_set_error' error='{e}' key='{key}'")
        except Exception as e:
            logger.error(f"action='redis_set_unexpected_error' error='{e}' key='{key}'")

    def _save_to_db(
        self,
        db: Session,
        city: str,
        temperature: float,
        description: str,
        humidity: int,
        units: str,
        is_cached: bool,
    ) -> WeatherRequest:
        """Сохраняет запрос в БД"""
        weather_request = WeatherRequest(
            city=city,
            temperature=temperature,
            description=description,
            humidity=humidity,
            units=units,
            is_cached=is_cached,
        )
        db.add(weather_request)
        db.commit()
        db.refresh(weather_request)
        return weather_request

    async def get_or_fetch(
        self, db: Session, city: str, units: TemperatureUnit
    ) -> WeatherRequest:
        """
        Основной метод: пытается получить из кэша,
        если нет - запрашивает из API
        """
        city = city.strip()
        cache_key = self._make_cache_key(city, units)
        db_units_letter = units.to_db_letter()

        cached_data = await self._get_from_redis(cache_key)

        if cached_data:
            logger.info(
                f"action='weather_from_cache' "
                f"city='{cached_data['city']}' units='{db_units_letter}'"
            )
            return self._save_to_db(
                db=db,
                city=cached_data["city"],
                temperature=cached_data["temperature"],
                description=cached_data["description"],
                humidity=cached_data["humidity"],
                units=db_units_letter,
                is_cached=True,
            )

        api_units = units.to_api_units()
        weather_data = await self.api_client.get_current_weather(city, api_units)

        if not weather_data:
            return None

        try:
            temp = weather_data["main"]["temp"]
            humidity = weather_data["main"]["humidity"]
            description = weather_data["weather"][0]["description"]
            resolved_city_name = weather_data["name"]
        except KeyError as e:
            logger.error(
                f"action='parse_api_response_error' "
                f"error='{e}' response_keys={list(weather_data.keys())}"
            )
            raise

        cache_payload = {
            "city": resolved_city_name,
            "temperature": temp,
            "description": description,
            "humidity": humidity,
        }
        await self._save_to_redis(cache_key, cache_payload)

        return self._save_to_db(
            db=db,
            city=resolved_city_name,
            temperature=temp,
            description=description,
            humidity=humidity,
            units=db_units_letter,
            is_cached=False,
        )
