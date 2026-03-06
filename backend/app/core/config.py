from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI Trading App"
    DEBUG: bool = False
    API_VERSION: str = "v1"
    SECRET_KEY: str = "35d2b8a3056fb746d05198f69c0b485f93cd49d8c76c7f5648eda25ea4d56dc0"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://trader:trader123@localhost:5432/trading_db"
    DATABASE_SYNC_URL: str = "postgresql://trader:trader123@localhost:5432/trading_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Angel One SmartAPI
    ANGEL_ONE_API_KEY: str = ""
    ANGEL_ONE_CLIENT_ID: str = ""
    ANGEL_ONE_PASSWORD: str = ""
    ANGEL_ONE_TOTP_SECRET: str = ""  # Base32 TOTP secret

    # Alpaca (US market fallback / paper trading)
    ALPACA_API_KEY: str = ""
    ALPACA_SECRET_KEY: str = ""
    ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets"

    # Polygon.io
    POLYGON_API_KEY: str = ""

    # Market data source preference order
    MARKET_DATA_PRIMARY: str = "angel_one"   # angel_one | alpaca | polygon | yfinance
    MARKET_DATA_FALLBACK: str = "yfinance"

    # AI Engine
    SIGNAL_CONFIDENCE_THRESHOLD: float = 0.65  # 65% minimum
    MAX_SIGNALS_PER_DAY: int = 20

    # CORS
    ALLOWED_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Market hours (IST) — NSE/BSE
    MARKET_OPEN_TIME: str = "09:15"
    MARKET_CLOSE_TIME: str = "15:30"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
