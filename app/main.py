import logging
from fastapi import FastAPI
from app.config import settings
from app.api.v1.weather import router as weather_router

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

app.include_router(weather_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Weather Service API приветствует тебя! Перейди на /docs для Swagger UI."}