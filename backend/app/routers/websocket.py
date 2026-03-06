"""
WebSocket router for real-time price streaming.
Clients connect and subscribe to symbols.
Server pushes price updates every second.
"""
import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError

from app.core.security import decode_access_token
from app.services.market_data import MarketDataService
from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])
market_svc = MarketDataService()


class ConnectionManager:
    """Manages WebSocket connections and subscriptions."""

    def __init__(self):
        # user_id -> set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # websocket -> subscribed symbols
        self.subscriptions: Dict[WebSocket, Set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        self.subscriptions[websocket] = set()
        logger.info(f"WebSocket connected: user {user_id}")

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
        self.subscriptions.pop(websocket, None)
        logger.info(f"WebSocket disconnected: user {user_id}")

    def subscribe(self, websocket: WebSocket, symbols: list):
        if websocket in self.subscriptions:
            self.subscriptions[websocket].update(s.upper() for s in symbols)

    def unsubscribe(self, websocket: WebSocket, symbols: list):
        if websocket in self.subscriptions:
            for s in symbols:
                self.subscriptions[websocket].discard(s.upper())

    async def send_to(self, websocket: WebSocket, data: dict):
        try:
            await websocket.send_json(data)
        except Exception:
            pass

    async def broadcast_to_user(self, user_id: int, data: dict):
        for ws in list(self.active_connections.get(user_id, [])):
            await self.send_to(ws, data)


manager = ConnectionManager()


async def _stream_prices(websocket: WebSocket, user_id: int, angel_service=None):
    """Background task: push live prices to client every second."""
    while True:
        try:
            subs = manager.subscriptions.get(websocket, set())
            if not subs:
                await asyncio.sleep(1)
                continue

            price_updates = []
            for symbol in list(subs):
                # Get from cache first (populated by Angel One WS or polling)
                quote = await market_svc.get_quote(symbol, "NSE", angel_service)
                if quote:
                    price_updates.append({
                        "symbol": quote.symbol,
                        "ltp": quote.ltp,
                        "change": quote.change,
                        "change_percent": quote.change_percent,
                        "volume": quote.volume,
                        "high": quote.high,
                        "low": quote.low,
                        "open": quote.open,
                        "vwap": quote.avg_price,
                        "timestamp": quote.timestamp,
                    })

            if price_updates:
                await manager.send_to(websocket, {
                    "type": "price_update",
                    "data": price_updates,
                })

            await asyncio.sleep(1)  # 1-second update interval
        except Exception as e:
            logger.debug(f"Stream error: {e}")
            break


@router.websocket("/ws/market")
async def market_websocket(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time market data.

    Connect with: ws://localhost:8000/ws/market?token=<JWT>

    Messages (client → server):
      {"action": "subscribe", "symbols": ["RELIANCE", "TCS"]}
      {"action": "unsubscribe", "symbols": ["TCS"]}
      {"action": "ping"}

    Messages (server → client):
      {"type": "price_update", "data": [{...}, ...]}
      {"type": "signal_alert", "data": {...}}
      {"type": "error", "message": "..."}
    """
    # Authenticate via JWT token in query param
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = int(payload.get("sub", 0))
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token")
        return

    # Load user for Angel One service
    from app.core.database import AsyncSessionLocal
    from app.models.user import User
    from sqlalchemy import select
    angel_service = None
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user and user.angel_one_api_key:
            from app.services.angel_one import get_angel_one_service
            angel_service = get_angel_one_service(
                user.id, user.angel_one_api_key,
                user.angel_one_client_id, user.angel_one_password,
                user.angel_one_totp_secret
            )

    await manager.connect(websocket, user_id)

    # Start price streaming in background
    stream_task = asyncio.create_task(_stream_prices(websocket, user_id, angel_service))

    try:
        await manager.send_to(websocket, {
            "type": "connected",
            "message": "Connected to live market feed",
            "user_id": user_id,
        })

        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                msg = json.loads(raw)
                action = msg.get("action")

                if action == "subscribe":
                    symbols = msg.get("symbols", [])
                    manager.subscribe(websocket, symbols)
                    await manager.send_to(websocket, {
                        "type": "subscribed",
                        "symbols": symbols,
                    })

                elif action == "unsubscribe":
                    symbols = msg.get("symbols", [])
                    manager.unsubscribe(websocket, symbols)

                elif action == "ping":
                    await manager.send_to(websocket, {"type": "pong"})

            except asyncio.TimeoutError:
                # Send heartbeat
                await manager.send_to(websocket, {"type": "heartbeat"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        stream_task.cancel()
        manager.disconnect(websocket, user_id)


async def broadcast_signal_alert(user_id: int, signal: dict):
    """Called by background tasks to push signal alerts to users."""
    await manager.broadcast_to_user(user_id, {
        "type": "signal_alert",
        "data": signal,
    })
