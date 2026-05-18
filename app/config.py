from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Weather Service"
    DEBUG: bool = False

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    DATABASE_URL: str

    WEATHER_API_KEY: str
    WEATHER_API_URL: str

    RATE_LIMIT_PER_MINUTE: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()