from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    APP_ENV: str = "dev"
    SECRET_KEY: str = "change_me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    DATABASE_URL: str = "sqlite+aiosqlite:///./dev.db"
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    class Config:
        env_file = ".env"

    def normalized_db_url(self) -> str:
        url = self.DATABASE_URL
        # Railway/Heroku style 'postgres://' → 'postgresql+psycopg://'
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://") and "+psycopg" not in url and "+asyncpg" not in url:
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url

settings = Settings()
