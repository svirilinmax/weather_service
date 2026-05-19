import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.health import router as health_router
from app.api.v1.weather import router as weather_router
from app.config import settings
from app.core.limiter import limiter
from app.middlewares.logging_middleware import LoggingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:time='%(asctime)s' %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI(title=settings.PROJECT_NAME, debug=settings.DEBUG, version="1.0.0")

app.add_middleware(LoggingMiddleware)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(weather_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {
        "message": "Weather Service API приветствует тебя! "
        "Перейди на /docs для Swagger UI."
    }


@app.get("/weather", response_class=HTMLResponse)
async def weather_page():
    """HTML страница с интерфейсом для пользователя"""
    html_path = Path("app/templates/index.html")
    if html_path.exists():
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    return HTMLResponse(
        content="<h1>Weather Service</h1><p>Template not found</p>", status_code=404
    )
