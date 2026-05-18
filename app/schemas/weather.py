from datetime import datetime
from pydantic import BaseModel
from typing import List

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

class WeatherHistoryItem(BaseModel):
    id: int
    city: str
    temperature: float
    description: str
    humidity: int
    units: str
    is_cached: bool
    timestamp: datetime

    class Config:
        from_attributes = True

class WeatherHistoryResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[WeatherHistoryItem]