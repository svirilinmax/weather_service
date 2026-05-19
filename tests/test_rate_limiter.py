from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.config import settings
from app.models.weather import WeatherRequest


def test_rate_limiter_blocks_weather_requests(client_with_limiter):
    """Тестируем rate limiter на эндпоинте /weather"""

    now = datetime.now(timezone.utc)

    mock_weather_request = WeatherRequest(
        city="London",
        temperature=15.5,
        description="облачно",
        humidity=70,
        units="C",
        is_cached=False,
        timestamp=now,
    )

    with patch("app.api.v1.weather.cache_service") as mock_service:
        mock_service.get_or_fetch = AsyncMock(return_value=mock_weather_request)

        responses = []
        limit = settings.RATE_LIMIT_PER_MINUTE

        for i in range(limit + 5):
            response = client_with_limiter.get(
                "/api/v1/weather?city=London&units=celsius"
            )
            responses.append(response.status_code)
            if response.status_code == 429:
                break

        assert 429 in responses, f"Rate limiter не сработал! Статусы: {responses}"

        successful_requests = sum(1 for r in responses if r == 200)
        assert (
            successful_requests <= limit
        ), f"Слишком много успешных запросов: {successful_requests} > {limit}"
