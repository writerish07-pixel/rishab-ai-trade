import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import settings
from app.core.database import init_db
from app.core.redis_client import get_redis, close_redis
from app.routers import auth, market, orders, portfolio, signals, websocket

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting AI Trading App backend...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Initialize Redis
    await get_redis()
    logger.info("Redis connected")

    yield  # App is running

    # Cleanup
    await close_redis()
    logger.info("Shutting down...")


app = FastAPI(
    title="AI Trading App API",
    description="""
## Professional AI-Powered Intraday Trading System

### Features
- **Angel One SmartAPI** integration for real-time order execution
- **AI Signal Engine** with 65-70%+ accuracy intraday signals
- **Technical Analysis** with VWAP, RSI, MACD, EMA, Bollinger Bands
- **Pattern Detection** for breakouts, reversals, gap plays
- **Institutional Tracker** for FII/DII/MF activity analysis
- **WebSocket Streaming** for sub-second price updates
- **F&O Support** with option chain and PCR analysis
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again."},
    )


# Health check
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "1.0.0",
    }


# Include routers
PREFIX = f"/api/{settings.API_VERSION}"
app.include_router(auth.router, prefix=PREFIX)
app.include_router(market.router, prefix=PREFIX)
app.include_router(orders.router, prefix=PREFIX)
app.include_router(portfolio.router, prefix=PREFIX)
app.include_router(signals.router, prefix=PREFIX)
app.include_router(websocket.router)  # No prefix — WS at root


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
        ws_ping_interval=20,
        ws_ping_timeout=10,
    )
