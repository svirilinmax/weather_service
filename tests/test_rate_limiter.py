from app.config import settings


def test_rate_limiter_blocks_weather_requests(client_with_limiter, monkeypatch):
    """Тестируем rate limiter на эндпоинте /weather"""

    from app.services.weather_api import WeatherAPIClient

    mock_weather_data = {
        "name": "London",
        "main": {"temp": 15.5, "humidity": 70},
        "weather": [{"description": "облачно"}]
    }

    async def mock_get_current_weather(*args, **kwargs):
        return mock_weather_data

    monkeypatch.setattr(WeatherAPIClient, "get_current_weather", mock_get_current_weather)

    responses = []
    for i in range(settings.RATE_LIMIT_PER_MINUTE + 1):
        response = client_with_limiter.get("/api/v1/weather?city=London&units=celsius")
        responses.append(response.status_code)
        if response.status_code == 429:
            break

    assert 429 in responses, f"Rate limiter не сработал! Статусы: {responses}"

    history_response = client_with_limiter.get("/api/v1/weather/history?city=London")
    assert history_response.status_code == 200
    successful_requests = sum(1 for r in responses if r == 200)
    assert successful_requests <= settings.RATE_LIMIT_PER_MINUTE