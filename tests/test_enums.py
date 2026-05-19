from app.schemas.enums import TemperatureUnit


def test_temperature_unit_to_db_letter():
    """Тест конвертации в букву для БД"""
    assert TemperatureUnit.CELSIUS.to_db_letter() == "C"
    assert TemperatureUnit.FAHRENHEIT.to_db_letter() == "F"


def test_temperature_unit_to_api_units():
    """Тест конвертации в единицы для API"""
    assert TemperatureUnit.CELSIUS.to_api_units() == "metric"
    assert TemperatureUnit.FAHRENHEIT.to_api_units() == "imperial"


def test_temperature_unit_enum_values():
    """Тест значений enum"""
    assert TemperatureUnit.CELSIUS.value == "celsius"
    assert TemperatureUnit.FAHRENHEIT.value == "fahrenheit"