import csv
import logging
from datetime import datetime
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import settings
from app.core.limiter import limiter
from app.database import get_db
from app.models.weather import WeatherRequest
from app.schemas.enums import TemperatureUnit
from app.schemas.weather import WeatherHistoryResponse, WeatherResponse
from app.services.weather_cache import WeatherCacheService

logger = logging.getLogger("weather_logger")

router = APIRouter(prefix="/weather", tags=["Weather"])
cache_service = WeatherCacheService()


@router.get("", response_model=WeatherResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_weather(
    request: Request,
    city: str = Query(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Zа-яА-Я\s\-]+$",
        description="Название города (буквы, пробелы, дефисы)",
    ),
    units: TemperatureUnit = Query(
        TemperatureUnit.CELSIUS, description="Единица измерения"
    ),
    db: Session = Depends(get_db),
):
    weather_data = await cache_service.get_or_fetch(db, city, units)

    if not weather_data:
        raise HTTPException(
            status_code=404, detail="Город не найден или сервис погоды недоступен"
        )

    return weather_data


@router.get("/history", response_model=WeatherHistoryResponse)
async def get_weather_history(
    city: str = Query(
        None,
        min_length=1,
        max_length=100,
        description="Фильтр по названию города (подстрока)",
    ),
    date_from: datetime = Query(None, description="Дата ОТ"),
    date_to: datetime = Query(None, description="Дата ДО"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(
        10,
        ge=1,
        le=100,
        description="Количество элементов на странице (по умолчанию 10)",
    ),
    db: Session = Depends(get_db),
):
    query = db.query(WeatherRequest)

    if city:
        query = query.filter(WeatherRequest.city.ilike(f"%{city.strip()}%"))
    if date_from:
        query = query.filter(WeatherRequest.timestamp >= date_from)
    if date_to:
        query = query.filter(WeatherRequest.timestamp <= date_to)

    total_items = query.count()
    offset = (page - 1) * size
    records = (
        query.order_by(desc(WeatherRequest.timestamp)).offset(offset).limit(size).all()
    )

    return {"total": total_items, "page": page, "size": size, "items": records}


@router.get("/export")
async def export_history_to_csv(
    city: str = Query(None, min_length=1, max_length=100),
    date_from: datetime = Query(None),
    date_to: datetime = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(WeatherRequest)
    if city:
        query = query.filter(WeatherRequest.city.ilike(f"%{city.strip()}%"))
    if date_from:
        query = query.filter(WeatherRequest.timestamp >= date_from)
    if date_to:
        query = query.filter(WeatherRequest.timestamp <= date_to)

    records = query.order_by(desc(WeatherRequest.timestamp)).all()

    f = StringIO()
    writer = csv.writer(f)

    writer.writerow(
        [
            "ID",
            "Город",
            "Температура",
            "Описание",
            "Влажность",
            "Ед. Изм.",
            "Из Кэша",
            "Дата Запроса (UTC)",
        ]
    )

    for r in records:
        writer.writerow(
            [
                r.id,
                r.city,
                r.temperature,
                r.description,
                r.humidity,
                r.units,
                r.is_cached,
                r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            ]
        )

    f.seek(0)
    response = StreamingResponse(f, media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=weather_history.csv"
    return response
