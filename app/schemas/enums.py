from enum import Enum


class TemperatureUnit(str, Enum):
    CELSIUS = "celsius"
    FAHRENHEIT = "fahrenheit"

    def to_db_letter(self) -> str:
        return "C" if self == TemperatureUnit.CELSIUS else "F"

    def to_api_units(self) -> str:
        return "metric" if self == TemperatureUnit.CELSIUS else "imperial"
