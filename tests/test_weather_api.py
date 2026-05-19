from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.weather_api import WeatherAPIClient


@pytest.mark.asyncio
async def test_weather_api_timeout():
    """Тест таймаута внешнего API"""
    client = WeatherAPIClient()

    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Timeout")):
        result = await client.get_current_weather("London", "metric")
        assert result is None


@pytest.mark.asyncio
async def test_weather_api_http_error():
    """Тест HTTP ошибки внешнего API"""
    client = WeatherAPIClient()

    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        result = await client.get_current_weather("London", "metric")
        assert result is None


@pytest.mark.asyncio
async def test_weather_api_404_error():
    """Тест: город не найден (404)"""
    client = WeatherAPIClient()

    mock_response = AsyncMock()
    mock_response.status_code = 404

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        result = await client.get_current_weather("NonExistentCity", "metric")
        assert result is None


@pytest.mark.asyncio
async def test_weather_api_success():
    """Тест успешного ответа от API"""
    client = WeatherAPIClient()

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = lambda: {"name": "London", "main": {"temp": 15.5}}

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        result = await client.get_current_weather("London", "metric")
        assert result is not None
        assert result["name"] == "London"
        assert result["main"]["temp"] == 15.5
