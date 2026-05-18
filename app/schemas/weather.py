from datetime import datetime
from pydantic import BaseModel, Field

class WeatherResponse(BaseModel):
    city: str
    temperature: float
    description: str
    humidity: int
    units: str
    is_cached: bool
    timestamp: datetime

    class Config:
        from_attributes = True