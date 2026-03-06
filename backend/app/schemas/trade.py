from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.trade import OrderType, OrderSide, ProductType, Exchange, OrderStatus


class PlaceOrderRequest(BaseModel):
    symbol: str = Field(..., example="RELIANCE")
    exchange: Exchange = Field(default=Exchange.NSE)
    order_type: OrderType = Field(default=OrderType.MARKET)
    order_side: OrderSide
    product_type: ProductType = Field(default=ProductType.INTRADAY)
    quantity: int = Field(..., gt=0)
    price: float = Field(default=0.0, ge=0)
    trigger_price: float = Field(default=0.0, ge=0)

    # Bracket order fields
    square_off: Optional[float] = None
    stoploss: Optional[float] = None
    trailing_stoploss: Optional[float] = None

    # F&O fields
    strike_price: Optional[float] = None
    option_type: Optional[str] = None   # CE / PE
    expiry_date: Optional[str] = None

    signal_id: Optional[int] = None


class ModifyOrderRequest(BaseModel):
    order_id: str
    quantity: Optional[int] = None
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    order_type: Optional[OrderType] = None


class CancelOrderRequest(BaseModel):
    order_id: str
    variety: str = "NORMAL"


class TradeResponse(BaseModel):
    id: int
    symbol: str
    exchange: str
    order_type: str
    order_side: str
    product_type: str
    quantity: int
    price: float
    status: str
    angel_one_order_id: Optional[str]
    executed_price: float
    executed_qty: int
    pnl: float
    is_algo_order: bool
    created_at: datetime

    class Config:
        from_attributes = True


class OrderBookItem(BaseModel):
    order_id: str
    symbol: str
    exchange: str
    order_type: str
    transaction_type: str
    product_type: str
    quantity: int
    price: float
    status: str
    order_time: str
