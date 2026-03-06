import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.trade import Trade, OrderStatus
from app.schemas.trade import PlaceOrderRequest, ModifyOrderRequest, CancelOrderRequest, TradeResponse, OrderBookItem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orders", tags=["Orders"])


def _get_angel_service(user: User):
    if not user.angel_one_api_key:
        raise HTTPException(status_code=400, detail="Angel One account not connected. Go to Settings > Connect Angel One.")
    from app.services.angel_one import get_angel_one_service
    return get_angel_one_service(
        user.id, user.angel_one_api_key,
        user.angel_one_client_id, user.angel_one_password,
        user.angel_one_totp_secret
    )


@router.post("/place", response_model=dict)
async def place_order(
    payload: PlaceOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Place a BUY or SELL order via Angel One."""
    angel = _get_angel_service(current_user)

    # Look up the symbol token (required by Angel One)
    token_results = await angel.search_scrip(payload.exchange.value, payload.symbol)
    if not token_results:
        raise HTTPException(status_code=404, detail=f"Symbol {payload.symbol} not found on {payload.exchange}")

    token = token_results[0].get("symboltoken", "")

    order_params = {
        "symbol": payload.symbol,
        "exchange": payload.exchange.value,
        "order_type": payload.order_type.value,
        "order_side": payload.order_side.value,
        "product_type": payload.product_type.value,
        "quantity": payload.quantity,
        "price": payload.price,
        "trigger_price": payload.trigger_price,
        "token": token,
        "square_off": payload.square_off or 0,
        "stoploss": payload.stoploss or 0,
        "variety": "BRACKET" if payload.order_type.value == "BRACKET" else "NORMAL",
    }

    result = await angel.place_order(order_params)
    if not result or result.get("status") in ("FAILED", "ERROR"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "Order placement failed") if result else "Order placement failed"
        )

    # Log the trade in our DB
    trade = Trade(
        user_id=current_user.id,
        symbol=payload.symbol,
        exchange=payload.exchange.value,
        order_type=payload.order_type.value,
        order_side=payload.order_side.value,
        product_type=payload.product_type.value,
        quantity=payload.quantity,
        price=payload.price,
        trigger_price=payload.trigger_price,
        status=OrderStatus.OPEN,
        angel_one_order_id=result.get("order_id"),
        signal_id=payload.signal_id,
        is_algo_order=bool(payload.signal_id),
    )
    db.add(trade)
    await db.commit()
    await db.refresh(trade)

    logger.info(f"Order placed: {payload.order_side} {payload.quantity} {payload.symbol} | Order ID: {result.get('order_id')}")
    return {
        "order_id": result.get("order_id"),
        "trade_id": trade.id,
        "status": "PLACED",
        "symbol": payload.symbol,
        "side": payload.order_side.value,
        "quantity": payload.quantity,
        "message": f"Order placed successfully. Order ID: {result.get('order_id')}",
    }


@router.post("/modify")
async def modify_order(
    payload: ModifyOrderRequest,
    current_user: User = Depends(get_current_user),
):
    """Modify an existing order."""
    angel = _get_angel_service(current_user)
    params = {
        "variety": "NORMAL",
        "orderid": payload.order_id,
        "ordertype": payload.order_type.value if payload.order_type else "LIMIT",
        "producttype": "INTRADAY",
        "duration": "DAY",
        "price": str(payload.price or 0),
        "quantity": str(payload.quantity or 0),
        "tradingsymbol": "",
        "symboltoken": "",
        "exchange": "NSE",
    }
    if payload.trigger_price:
        params["triggerprice"] = str(payload.trigger_price)

    result = await angel.modify_order(params)
    if not result:
        raise HTTPException(status_code=400, detail="Order modification failed")
    return {"status": "MODIFIED", "order_id": payload.order_id}


@router.post("/cancel")
async def cancel_order(
    payload: CancelOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an open order."""
    angel = _get_angel_service(current_user)
    result = await angel.cancel_order(payload.order_id, payload.variety)
    if not result or not result.get("status"):
        msg = result.get("message", "Order cancellation failed") if result else "Order cancellation failed"
        raise HTTPException(status_code=400, detail=msg)

    # Update trade status in DB
    res = await db.execute(
        select(Trade).where(
            Trade.angel_one_order_id == payload.order_id,
            Trade.user_id == current_user.id
        )
    )
    trade = res.scalar_one_or_none()
    if trade:
        trade.status = OrderStatus.CANCELLED
        db.add(trade)
        await db.commit()

    return {"status": "CANCELLED", "order_id": payload.order_id}


@router.get("/book", response_model=List[dict])
async def get_order_book(current_user: User = Depends(get_current_user)):
    """Fetch today's order book from Angel One."""
    angel = _get_angel_service(current_user)
    orders = await angel.get_order_book()
    return orders or []


@router.get("/history", response_model=List[TradeResponse])
async def get_order_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get trade history from our database."""
    result = await db.execute(
        select(Trade)
        .where(Trade.user_id == current_user.id)
        .order_by(Trade.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/margin")
async def get_margin(current_user: User = Depends(get_current_user)):
    """Get available margin / funds from Angel One."""
    angel = _get_angel_service(current_user)
    data = await angel.get_rms_data()
    return data or {}
