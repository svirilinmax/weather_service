import time
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import httpx
from app.database import get_db
from app.config import settings

router = APIRouter(prefix="", tags=["Infrastructure"])
logger = logging.getLogger("weather_logger")


async def check_external_api() -> tuple[bool, float]:
    """Проверяет доступность внешнего API погоды с таймаутом 2 секунды"""
    start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            params = {
                "q": "London",
                "appid": settings.WEATHER_API_KEY,
                "units": "metric"
            }
            response = await client.get(settings.WEATHER_API_URL, params=params)
            duration = round((time.time() - start_time) * 1000, 2)
            return response.status_code == 200, duration
    except Exception as e:
        duration = round((time.time() - start_time) * 1000, 2)
        logger.warning(f"action='external_api_health_check' status='unreachable' duration_ms={duration} error='{e}'")
        return False, duration


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    start_time = time.time()
    db_ok = False
    db_duration = 0

    try:
        db_start = time.time()
        db.execute(text("SELECT 1"))
        db_duration = round((time.time() - db_start) * 1000, 2)
        db_ok = True
    except Exception as e:
        logger.error(f"action='health_check_db_failed' error='{e}'")

    external_ok, external_duration = await check_external_api()

    total_duration = round((time.time() - start_time) * 1000, 2)

    if db_ok and external_ok:
        status = "healthy"
        http_status = 200
    elif db_ok and not external_ok:
        status = "degraded"
        http_status = 200
    else:
        status = "unhealthy"
        http_status = 503

    response_content = {
        "status": status,
        "database": "connected" if db_ok else "disconnected",
        "database_duration_ms": db_duration,
        "external_api": "reachable" if external_ok else "unreachable",
        "external_api_duration_ms": external_duration,
        "total_duration_ms": total_duration
    }

    if status == "unhealthy":
        return JSONResponse(status_code=http_status, content=response_content)

    return response_content