"""
Application settings, loaded from environment variables.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "DataGuard API"
    app_version: str = "0.1.0"

    postgres_user: str = "dataguard"
    postgres_password: str
    postgres_db: str = "dataguard"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    @property
    def database_url(self) -> URL:
        # URL.create escapes special characters in the password safely.
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
