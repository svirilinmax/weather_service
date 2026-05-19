import pytest
from sqlalchemy import text
from app.database import get_db, engine, SessionLocal


def test_get_db():
    """Тест получения сессии БД"""
    db_gen = get_db()
    db = next(db_gen)
    assert db is not None
    assert db.bind is not None

    with pytest.raises(StopIteration):
        next(db_gen)


def test_engine_connection():
    """Тест соединения с БД"""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_session_local():
    """Тест создания сессии"""
    session = SessionLocal()
    assert session is not None
    session.close()