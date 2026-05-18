import csv
from io import StringIO

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc




from app.database import get_db
from app.models.weather import WeatherRequest
from app.schemas.weather import WeatherResponse
from app.services.weather_api import WeatherAPIClient
from app.schemas.weather import WeatherHistoryResponse

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

@router.get("/history", response_model=WeatherHistoryResponse)
def get_weather_history(
        city: str = Query(None, description="Фильтр по названию города (подстрока)"),
        date_from: datetime = Query(None, description="Дата ОТ"),
        date_to: datetime = Query(None, description="Дата ДО"),
        page: int = Query(1, ge=1, description="Номер страницы"),
        size: int = Query(10, ge=1, le=100, description="Количество элементов на странице (по умолчанию 10)"),
        db: Session = Depends(get_db)
):
    query = db.query(WeatherRequest)

    if city:
        query = query.filter(WeatherRequest.city.ilike(f"%{city}%"))
    if date_from:
        query = query.filter(WeatherRequest.timestamp >= date_from)
    if date_to:
        query = query.filter(WeatherRequest.timestamp <= date_to)

    total_items = query.count()

    offset = (page - 1) * size
    records = query.order_by(desc(WeatherRequest.timestamp)).offset(offset).limit(size).all()

    return {
        "total": total_items,
        "page": page,
        "size": size,
        "items": records
    }


@router.get("/export")
def export_history_to_csv(
        city: str = Query(None),
        date_from: datetime = Query(None),
        date_to: datetime = Query(None),
        db: Session = Depends(get_db)
):
    query = db.query(WeatherRequest)
    if city:
        query = query.filter(WeatherRequest.city.ilike(f"%{city}%"))
    if date_from:
        query = query.filter(WeatherRequest.timestamp >= date_from)
    if date_to:
        query = query.filter(WeatherRequest.timestamp <= date_to)

    records = query.order_by(desc(WeatherRequest.timestamp)).all()

    f = StringIO()
    writer = csv.writer(f)

    writer.writerow(
        ["ID", "Город", "Температура", "Описание", "Влажность", "Ед. Изм.", "Из Кэша", "Дата Запроса (UTC)"])

    for r in records:
        writer.writerow([
            r.id, r.city, r.temperature, r.description,
            r.humidity, r.units, r.is_cached, r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        ])

    f.seek(0)

    response = StreamingResponse(f, media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=weather_history.csv"
    return response