import pytest

from app.database import get_db


def test_get_db():
    """Тест получения сессии БД"""
    db_gen = get_db()
    db = next(db_gen)
    assert db is not None
    assert db.bind is not None

    with pytest.raises(StopIteration):
        next(db_gen)
