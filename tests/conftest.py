from unittest.mock import patch
from urllib.parse import urlparse, urlunparse

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.core.limiter import limiter
from app.database import Base, get_db
from app.main import app
from app.services.weather_cache import WeatherCacheService


def get_test_database_url():
    url = urlparse(settings.DATABASE_URL)
    test_db_name = url.path[1:] + "_test" if url.path else "test_db"
    return urlunparse(url._replace(path=f"/{test_db_name}"))


TEST_DATABASE_URL = get_test_database_url()

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Создает чистую сессию БД для каждого теста"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Тестовый клиент FastAPI с отключенным rate limiter и замоканным Redis"""

    def _get_db_override():
        try:
            yield db_session
        finally:
            pass

    limiter.enabled = False

    fake_redis = fakeredis.FakeRedis(decode_responses=True)

    mock_cache_service = WeatherCacheService(redis_client=fake_redis)

    async def mock_get_or_fetch(db, city, units):
        return None

    mock_cache_service.get_or_fetch = mock_get_or_fetch

    with patch("app.api.v1.weather.cache_service", mock_cache_service):
        app.dependency_overrides[get_db] = _get_db_override

        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()
    limiter.enabled = True


@pytest.fixture(scope="function")
def client_with_limiter(db_session):
    """Тестовый клиент FastAPI С ВКЛЮЧЕННЫМ rate limiter и замоканным Redis"""

    def _get_db_override():
        try:
            yield db_session
        finally:
            pass

    limiter.enabled = True

    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    mock_cache_service = WeatherCacheService(redis_client=fake_redis)

    async def mock_get_or_fetch(db, city, units):
        return None

    mock_cache_service.get_or_fetch = mock_get_or_fetch

    with patch("app.api.v1.weather.cache_service", mock_cache_service):
        app.dependency_overrides[get_db] = _get_db_override

        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()
    limiter.enabled = False
