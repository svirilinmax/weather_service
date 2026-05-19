from datetime import datetime, timezone, timedelta
from app.models.weather import WeatherRequest


def test_get_history_with_pagination(client, db_session):
    """Тест пагинации"""
    for i in range(25):
        test_record = WeatherRequest(
            city=f"City{i}",
            temperature=20.0 + i,
            description="ясно",
            humidity=50,
            units="C",
            is_cached=False
        )
        db_session.add(test_record)
    db_session.commit()

    response = client.get("/api/v1/weather/history?page=1&size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 25
    assert data["page"] == 1
    assert data["size"] == 10
    assert len(data["items"]) == 10

    response = client.get("/api/v1/weather/history?page=2&size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert len(data["items"]) == 10


def test_get_history_with_filters(client, db_session):
    """Тест фильтрации по городу и датам"""
    now = datetime.now(timezone.utc)

    records = [
        WeatherRequest(city="Berlin", temperature=22.0, description="ясно", humidity=50, units="C",
                       timestamp=now - timedelta(days=1)),
        WeatherRequest(city="Munich", temperature=20.0, description="облачно", humidity=60, units="C", timestamp=now),
        WeatherRequest(city="Berlin", temperature=23.0, description="солнечно", humidity=45, units="C", timestamp=now),
    ]
    for r in records:
        db_session.add(r)
    db_session.commit()

    response = client.get("/api/v1/weather/history?city=Berlin")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(item["city"] == "Berlin" for item in data["items"])

    date_from = (now - timedelta(hours=12)).replace(microsecond=0, tzinfo=None).isoformat()
    date_to = (now + timedelta(hours=12)).replace(microsecond=0, tzinfo=None).isoformat()
    response = client.get(f"/api/v1/weather/history?date_from={date_from}&date_to={date_to}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


def test_get_history_empty(client):
    """Тест: история пуста"""
    response = client.get("/api/v1/weather/history")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_export_history_to_csv(client, db_session):
    """Тест экспорта истории в CSV"""
    test_record = WeatherRequest(
        city="Berlin",
        temperature=22.0,
        description="ясно",
        humidity=50,
        units="C",
        is_cached=False
    )
    db_session.add(test_record)
    db_session.commit()

    response = client.get("/api/v1/weather/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "weather_history.csv" in response.headers["content-disposition"]

    content = response.content.decode("utf-8")
    assert "Berlin" in content
    assert "22.0" in content
    assert "ясно" in content