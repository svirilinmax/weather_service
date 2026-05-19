import logging
import time
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger("weather_logger")


class WeatherAPIClient:
    def __init__(self):
        self.api_key = settings.WEATHER_API_KEY
        self.base_url = settings.WEATHER_API_URL

    async def get_current_weather(self, city: str, units: str) -> dict[str, Any] | None:
        """
        Запрашивает погоду у OpenWeatherMap.
        """
        params = {"q": city, "appid": self.api_key, "units": units, "lang": "ru"}

        start_time = time.time()
        async with httpx.AsyncClient(timeout=5.0) as client:
            logger.info(
                f"action='external_api_start' client='OpenWeatherMap' city='{city}'"
            )
            try:
                response = await client.get(self.base_url, params=params)
                duration = round((time.time() - start_time) * 1000, 2)
                logger.info(
                    f"action='external_api_end' city='{city}' "
                    f"duration_ms={duration} status_code={response.status_code}"
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.warning(f"action='external_api_not_found' city='{city}'")
                    return None
                else:
                    logger.error(
                        f"action='external_api_error' "
                        f"status_code={response.status_code} response='{response.text}'"
                    )
                    return None

            except httpx.RequestError as exc:
                duration = round((time.time() - start_time) * 1000, 2)
                logger.error(
                    f"action='external_api_timeout' "
                    f"duration_ms={duration} error='{exc}'"
                )
                return None
