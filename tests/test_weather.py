from unittest.mock import AsyncMock

from app.services.weather_api import WeatherAPIClient

MOCK_WEATHER_RESPONSE = {
    "name": "Paris",
    "main": {"temp": 18.5, "humidity": 65},
    "weather": [{"description": "переменная облачность"}],
}


def test_get_weather_success_and_caching(client, monkeypatch):
    """Тест кэширования: первый запрос из API, второй из кэша"""

    mock_get = AsyncMock(return_value=MOCK_WEATHER_RESPONSE)
    monkeypatch.setattr(WeatherAPIClient, "get_current_weather", mock_get)

    response1 = client.get("/api/v1/weather?city=Paris&units=celsius")
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["city"] == "Paris"
    assert data1["temperature"] == 18.5
    assert data1["is_cached"] is False
    assert mock_get.call_count == 1

    response2 = client.get("/api/v1/weather?city=Paris&units=celsius")
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["city"] == "Paris"
    assert data2["is_cached"] is True
    assert mock_get.call_count == 1


def test_get_weather_city_not_found(client, monkeypatch):
    """Тест: город не найден"""
    mock_get = AsyncMock(return_value=None)
    monkeypatch.setattr(WeatherAPIClient, "get_current_weather", mock_get)

    response = client.get("/api/v1/weather?city=NonExistentCity&units=celsius")
    assert response.status_code == 404
    assert response.json()["detail"] == "Город не найден или сервис погоды недоступен"
    assert mock_get.call_count == 1


def test_get_weather_different_units_cached_separately(client, monkeypatch):
    """Тест: кэш для разных единиц измерения независим"""
    mock_get = AsyncMock(return_value=MOCK_WEATHER_RESPONSE)
    monkeypatch.setattr(WeatherAPIClient, "get_current_weather", mock_get)

    response_c = client.get("/api/v1/weather?city=Paris&units=celsius")
    assert response_c.status_code == 200
    assert response_c.json()["units"] == "C"
    assert response_c.json()["is_cached"] is False

    response_f = client.get("/api/v1/weather?city=Paris&units=fahrenheit")
    assert response_f.status_code == 200
    assert response_f.json()["units"] == "F"
    assert response_f.json()["is_cached"] is False

    assert mock_get.call_count == 2
