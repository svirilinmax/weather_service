import time
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db

router = APIRouter(prefix="/health", tags=["Infrastructure"])
logger = logging.getLogger("weather_logger")


@router.get("")
def health_check(db: Session = Depends(get_db)):
    start_time = time.time()
    try:
        db.execute(text("SELECT 1"))
        duration = round((time.time() - start_time) * 1000, 2)

        return {
            "status": "healthy",
            "database": "connected",
            "duration_ms": duration
        }
    except Exception as e:
        logger.error(f"action='health_check_failed' error='{e}'")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "details": str(e)
            }
        )