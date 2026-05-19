from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict


class WeatherResponse(BaseModel):
    city: str
    temperature: float
    description: str
    humidity: int
    units: str
    is_cached: bool
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class WeatherHistoryItem(BaseModel):
    id: int
    city: str
    temperature: float
    description: str
    humidity: int
    units: str
    is_cached: bool
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class WeatherHistoryResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[WeatherHistoryItem]
