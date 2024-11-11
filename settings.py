from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class DotEnvSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class BotSettings(DotEnvSettings):
    model_config = SettingsConfigDict(env_prefix="API_")
    token: str = Field(default=...)


class DBSettings(DotEnvSettings):
    model_config = SettingsConfigDict(env_prefix="DB_")
    url: str = Field(default=...)


class Settings(DotEnvSettings):
    bot: BotSettings = BotSettings()
    db: DBSettings = DBSettings()


# Инициализация настроек
settings = Settings()
