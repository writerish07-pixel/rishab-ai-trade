"""
Angel One SmartAPI integration.
Docs: https://smartapi.angelbroking.com/docs
"""
import asyncio
import logging
import pyotp
import aiohttp
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

from app.core.config import settings
from app.core.redis_client import cache_set, cache_get, publish_market_data

logger = logging.getLogger(__name__)


# NSE token map for common indices (add more as needed)
INDEX_TOKENS = {
    "NIFTY50": {"exchange": "NSE", "token": "26000", "symbol": "Nifty 50"},
    "BANKNIFTY": {"exchange": "NSE", "token": "26009", "symbol": "Nifty Bank"},
    "SENSEX": {"exchange": "BSE", "token": "1", "symbol": "SENSEX"},
    "FINNIFTY": {"exchange": "NSE", "token": "26037", "symbol": "Nifty Fin Service"},
}


class AngelOneService:
    def __init__(self, api_key: str, client_id: str, password: str, totp_secret: str):
        self.api_key = api_key
        self.client_id = client_id
        self.password = password
        self.totp_secret = totp_secret
        self._smart_api: Optional[SmartConnect] = None
        self._jwt_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._ws: Optional[SmartWebSocketV2] = None
        self._ws_callbacks: list = []

    def _generate_totp(self) -> str:
        totp = pyotp.TOTP(self.totp_secret)
        return totp.now()

    async def login(self) -> bool:
        """Authenticate with Angel One SmartAPI."""
        try:
            loop = asyncio.get_event_loop()
            self._smart_api = SmartConnect(api_key=self.api_key)

            totp_value = self._generate_totp()
            data = await loop.run_in_executor(
                None,
                lambda: self._smart_api.generateSession(
                    self.client_id, self.password, totp_value
                )
            )

            if data.get("status"):
                self._jwt_token = data["data"]["jwtToken"]
                self._refresh_token = data["data"]["refreshToken"]
                self._token_expiry = datetime.utcnow() + timedelta(hours=8)

                # Cache the tokens
                await cache_set("angel_one_jwt", self._jwt_token, ttl=28800)
                await cache_set("angel_one_refresh", self._refresh_token, ttl=86400)

                logger.info(f"Angel One login successful for {self.client_id}")
                return True
            else:
                logger.error(f"Angel One login failed: {data.get('message')}")
                return False

        except Exception as e:
            logger.error(f"Angel One login error: {e}")
            return False

    async def ensure_authenticated(self) -> bool:
        """Ensure we have valid credentials, refresh if needed."""
        if self._smart_api is None or self._token_expiry is None:
            return await self.login()
        if datetime.utcnow() >= self._token_expiry - timedelta(minutes=10):
            return await self._refresh_session()
        return True

    async def _refresh_session(self) -> bool:
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: self._smart_api.generateToken(self._refresh_token)
            )
            if data.get("status"):
                self._jwt_token = data["data"]["jwtToken"]
                self._token_expiry = datetime.utcnow() + timedelta(hours=8)
                await cache_set("angel_one_jwt", self._jwt_token, ttl=28800)
                return True
            return await self.login()  # fallback to full login
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return await self.login()

    async def get_quote(self, exchange: str, tokens: List[str]) -> Optional[dict]:
        """Get real-time quote for given token(s)."""
        cache_key = f"quote:{exchange}:{':'.join(tokens)}"
        cached = await cache_get(cache_key)
        if cached:
            return cached

        try:
            await self.ensure_authenticated()
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: self._smart_api.getMarketData(
                    "FULL",
                    {exchange: tokens}
                )
            )
            if data.get("status"):
                result = data.get("data", {})
                await cache_set(cache_key, result, ttl=2)  # 2-second cache
                return result
        except Exception as e:
            logger.error(f"Get quote error: {e}")
        return None

    async def get_candle_data(
        self, exchange: str, symbol_token: str,
        interval: str = "ONE_MINUTE",
        from_date: str = None, to_date: str = None
    ) -> Optional[List]:
        """Fetch historical OHLCV candle data."""
        if not from_date:
            from_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        if not to_date:
            to_date = datetime.now().strftime("%Y-%m-%d %H:%M")

        cache_key = f"candles:{exchange}:{symbol_token}:{interval}"
        cached = await cache_get(cache_key)
        if cached:
            return cached

        try:
            await self.ensure_authenticated()
            loop = asyncio.get_event_loop()
            param = {
                "exchange": exchange,
                "symboltoken": symbol_token,
                "interval": interval,
                "fromdate": from_date,
                "todate": to_date,
            }
            data = await loop.run_in_executor(
                None, lambda: self._smart_api.getCandleData(param)
            )
            if data.get("status") and data.get("data"):
                candles = data["data"]
                await cache_set(cache_key, candles, ttl=60)
                return candles
        except Exception as e:
            logger.error(f"Candle data error: {e}")
        return None

    async def place_order(self, order_params: dict) -> Optional[dict]:
        """Place an order via Angel One SmartAPI."""
        try:
            await self.ensure_authenticated()
            loop = asyncio.get_event_loop()

            # Map our schema to Angel One format
            angel_order = {
                "variety": order_params.get("variety", "NORMAL"),
                "tradingsymbol": order_params["symbol"],
                "symboltoken": order_params.get("token", ""),
                "transactiontype": order_params["order_side"],   # BUY / SELL
                "exchange": order_params.get("exchange", "NSE"),
                "ordertype": self._map_order_type(order_params["order_type"]),
                "producttype": self._map_product_type(order_params["product_type"]),
                "duration": "DAY",
                "price": str(order_params.get("price", 0)),
                "squareoff": str(order_params.get("square_off", 0)),
                "stoploss": str(order_params.get("stoploss", 0)),
                "quantity": str(order_params["quantity"]),
            }
            if order_params.get("trigger_price"):
                angel_order["triggerprice"] = str(order_params["trigger_price"])

            data = await loop.run_in_executor(
                None, lambda: self._smart_api.placeOrder(angel_order)
            )
            if data.get("status"):
                logger.info(f"Order placed: {data['data']['orderid']} for {order_params['symbol']}")
                return {"order_id": data["data"]["orderid"], "status": "PLACED", "raw": data}
            else:
                logger.error(f"Order failed: {data.get('message')}")
                return {"status": "FAILED", "message": data.get("message"), "raw": data}
        except Exception as e:
            logger.error(f"Place order error: {e}")
            return {"status": "ERROR", "message": str(e)}

    async def cancel_order(self, order_id: str, variety: str = "NORMAL") -> Optional[dict]:
        try:
            await self.ensure_authenticated()
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None, lambda: self._smart_api.cancelOrder(order_id, variety)
            )
            return data
        except Exception as e:
            logger.error(f"Cancel order error: {e}")
            return None

    async def modify_order(self, params: dict) -> Optional[dict]:
        try:
            await self.ensure_authenticated()
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None, lambda: self._smart_api.modifyOrder(params)
            )
            return data
        except Exception as e:
            logger.error(f"Modify order error: {e}")
            return None

    async def get_order_book(self) -> Optional[List]:
        """Fetch today's order book."""
        try:
            await self.ensure_authenticated()
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, self._smart_api.orderBook)
            if data.get("status"):
                return data.get("data", [])
        except Exception as e:
            logger.error(f"Order book error: {e}")
        return []

    async def get_positions(self) -> Optional[List]:
        """Fetch current open positions."""
        cache_key = "positions"
        cached = await cache_get(cache_key)
        if cached:
            return cached
        try:
            await self.ensure_authenticated()
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, self._smart_api.position)
            if data.get("status") and data.get("data"):
                await cache_set(cache_key, data["data"], ttl=10)
                return data["data"]
        except Exception as e:
            logger.error(f"Positions error: {e}")
        return []

    async def get_holdings(self) -> Optional[List]:
        """Fetch portfolio holdings."""
        cache_key = "holdings"
        cached = await cache_get(cache_key)
        if cached:
            return cached
        try:
            await self.ensure_authenticated()
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, self._smart_api.holding)
            if data.get("status") and data.get("data"):
                await cache_set(cache_key, data["data"], ttl=60)
                return data["data"]
        except Exception as e:
            logger.error(f"Holdings error: {e}")
        return []

    async def get_rms_data(self) -> Optional[dict]:
        """Get Risk Management (margin) data."""
        try:
            await self.ensure_authenticated()
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, self._smart_api.rmsLimit)
            if data.get("status"):
                return data.get("data", {})
        except Exception as e:
            logger.error(f"RMS data error: {e}")
        return {}

    async def get_option_chain(self, name: str, expiry_date: str, strike_price: float) -> Optional[dict]:
        """Fetch option chain data."""
        try:
            await self.ensure_authenticated()
            loop = asyncio.get_event_loop()
            params = {
                "name": name,
                "expirydate": expiry_date,
                "strikeprice": str(strike_price),
            }
            data = await loop.run_in_executor(
                None, lambda: self._smart_api.optionGreek(params)
            )
            if data.get("status"):
                return data.get("data", {})
        except Exception as e:
            logger.error(f"Option chain error: {e}")
        return {}

    async def search_scrip(self, exchange: str, query: str) -> Optional[List]:
        """Search for a stock symbol token."""
        try:
            await self.ensure_authenticated()
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None, lambda: self._smart_api.searchScrip(exchange, query)
            )
            if data.get("status"):
                return data.get("data", [])
        except Exception as e:
            logger.error(f"Search scrip error: {e}")
        return []

    def start_websocket_feed(self, tokens: List[dict], callback):
        """Start WebSocket market data streaming."""
        try:
            self._ws = SmartWebSocketV2(
                self._jwt_token,
                self.api_key,
                self.client_id,
                self._refresh_token,
            )

            def on_data(wsapp, message):
                asyncio.create_task(callback(message))

            def on_error(wsapp, error):
                logger.error(f"WebSocket error: {error}")

            def on_close(wsapp):
                logger.info("WebSocket connection closed")

            def on_open(wsapp):
                logger.info("WebSocket connected, subscribing to feeds...")
                self._ws.subscribe("abc123", 3, tokens)  # mode 3 = SNAP_QUOTE

            self._ws.on_open = on_open
            self._ws.on_data = on_data
            self._ws.on_error = on_error
            self._ws.on_close = on_close
            self._ws.connect()
        except Exception as e:
            logger.error(f"WebSocket start error: {e}")

    def _map_order_type(self, order_type: str) -> str:
        mapping = {
            "MARKET": "MARKET",
            "LIMIT": "LIMIT",
            "STOP_LOSS": "STOPLOSS_LIMIT",
            "STOP_LOSS_MARKET": "STOPLOSS_MARKET",
            "BRACKET": "MARKET",
        }
        return mapping.get(order_type, "MARKET")

    def _map_product_type(self, product_type: str) -> str:
        mapping = {
            "INTRADAY": "INTRADAY",
            "DELIVERY": "DELIVERY",
            "FUTURES": "CARRYFORWARD",
            "OPTIONS": "CARRYFORWARD",
        }
        return mapping.get(product_type, "INTRADAY")


# Singleton holder per user session
_angel_one_instances: Dict[int, AngelOneService] = {}


def get_angel_one_service(user_id: int, api_key: str, client_id: str, password: str, totp_secret: str) -> AngelOneService:
    """Get or create an Angel One service instance for a user."""
    if user_id not in _angel_one_instances:
        _angel_one_instances[user_id] = AngelOneService(api_key, client_id, password, totp_secret)
    return _angel_one_instances[user_id]
