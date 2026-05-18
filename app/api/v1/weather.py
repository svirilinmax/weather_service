import csv
import json
import logging
from io import StringIO
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
import redis

from app.database import get_db
from app.models.weather import WeatherRequest
from app.schemas.weather import WeatherResponse, WeatherHistoryResponse
from app.services.weather_api import WeatherAPIClient
from app.config import settings
from app.schemas.enums import TemperatureUnit
from app.core.limiter import limiter

logger = logging.getLogger("weather_logger")

router = APIRouter(prefix="/weather", tags=["Weather"])
weather_client = WeatherAPIClient()


redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


@router.get("", response_model=WeatherResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_weather(
        request: Request,
        city: str = Query(..., description="Название города"),
        units: TemperatureUnit = Query(TemperatureUnit.CELSIUS, description="Единица измерения"),
        db: Session = Depends(get_db)
):
    api_units = units.to_api_units()
    db_units_letter = units.to_db_letter()

    cache_key = f"weather:{city.lower().strip()}:{db_units_letter}"
    cached_data_raw = None

    try:
        cached_data_raw = redis_client.get(cache_key)
    except redis.ConnectionError as e:
        logger.error(f"action='redis_error' error='{e}' key='{cache_key}'")
    except Exception as e:
        logger.error(f"action='redis_unexpected_error' error='{e}' key='{cache_key}'")

    if cached_data_raw:
        try:
            cached_data = json.loads(cached_data_raw)
            new_request = WeatherRequest(
                city=cached_data["city"],
                temperature=cached_data["temperature"],
                description=cached_data["description"],
                humidity=cached_data["humidity"],
                units=db_units_letter,
                is_cached=True
            )
            db.add(new_request)
            db.commit()
            db.refresh(new_request)
            logger.info(f"action='weather_from_cache' city='{cached_data['city']}' units='{db_units_letter}'")
            return new_request
        except Exception as e:
            logger.error(f"action='cache_deserialize_error' error='{e}'")

    weather_data = await weather_client.get_current_weather(city, api_units)

    if not weather_data:
        raise HTTPException(status_code=404, detail="Город не найден или сервис погоды недоступен")

    try:
        temp = weather_data["main"]["temp"]
        humidity = weather_data["main"]["humidity"]
        description = weather_data["weather"][0]["description"]
        resolved_city_name = weather_data["name"]
    except KeyError as e:
        logger.error(f"action='parse_api_response_error' error='{e}' response_keys={list(weather_data.keys())}")
        raise HTTPException(status_code=500, detail="Ошибка парсинга данных внешнего API")

    cache_payload = {
        "city": resolved_city_name,
        "temperature": temp,
        "description": description,
        "humidity": humidity
    }

    try:
        redis_client.setex(cache_key, settings.WEATHER_CACHE_TTL_SECONDS, json.dumps(cache_payload))
        logger.info(f"action='cache_set' key='{cache_key}' ttl={settings.WEATHER_CACHE_TTL_SECONDS}")
    except redis.ConnectionError as e:
        logger.error(f"action='redis_set_error' error='{e}' key='{cache_key}'")
    except Exception as e:
        logger.error(f"action='redis_set_unexpected_error' error='{e}' key='{cache_key}'")

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
async def get_weather_history(
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
async def export_history_to_csv(
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