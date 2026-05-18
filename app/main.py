import logging
from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.api.v1.weather import router as weather_router
from app.api.v1.health import router as health_router
from app.middlewares.logging_middleware import LoggingMiddleware
from app.core.limiter import limiter

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:time='%(asctime)s' %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    version="1.0.0"
)

app.add_middleware(LoggingMiddleware)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(weather_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Weather Service API приветствует тебя! Перейди на /docs для Swagger UI."}