from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.weather import WeatherRequest
from app.schemas.weather import WeatherResponse
from app.services.weather_api import WeatherAPIClient

router = APIRouter(prefix="/weather", tags=["Weather"])
weather_client = WeatherAPIClient()


@router.get("", response_model=WeatherResponse)
async def get_weather(
        city: str = Query(..., description="Название города"),
        units: str = Query("celsius", description="Единица измерения: Celsius или Fahrenheit"),
        db: Session = Depends(get_db)
):
    api_units = "metric" if units == "celsius" else "imperial"
    db_units_letter = "C" if units == "celsius" else "F"
    time_threshold = datetime.now(timezone.utc) - timedelta(minutes=5)

    cached_record = db.query(WeatherRequest).filter(WeatherRequest.city.ilike(city),
        WeatherRequest.units == db_units_letter,
        WeatherRequest.timestamp >= time_threshold
    ).order_by(desc(WeatherRequest.timestamp)).first()

    if cached_record:
        new_request = WeatherRequest(
            city=cached_record.city,
            temperature=cached_record.temperature,
            description=cached_record.description,
            humidity=cached_record.humidity,
            units=db_units_letter,
            is_cached=True
        )
        db.add(new_request)
        db.commit()
        db.refresh(new_request)
        return new_request

    weather_data = await weather_client.get_current_weather(city, api_units)

    if not weather_data:
        raise HTTPException(status_code=404, detail="Город не найден или сервис погоды недоступен")

    try:
        temp = weather_data["main"]["temp"]
        humidity = weather_data["main"]["humidity"]
        description = weather_data["weather"][0]["description"]
        resolved_city_name = weather_data["name"]
    except KeyError:
        raise HTTPException(status_code=500, detail="Ошибка парсинга данных внешнего API")

    new_request = WeatherRequest(
        city=resolved_city_name,
        temperature=temp,
        description=description,
        humidity=humidity,
        units=db_units_letter,
        is_cached=False
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    return new_request