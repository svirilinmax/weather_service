from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String

from app.database import Base


class WeatherRequest(Base):
    __tablename__ = "weather_requests"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, index=True, nullable=False)
    temperature = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    humidity = Column(Integer, nullable=False)
    units = Column(String(1), nullable=False)
    is_cached = Column(Boolean, default=False, nullable=False)
    timestamp = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        Index("idx_city_timestamp", "city", "timestamp"),
        Index("idx_timestamp", "timestamp"),
    )
