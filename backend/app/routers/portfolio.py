from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio, Holding, Position
from app.services.market_data import MarketDataService

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])
market_svc = MarketDataService()


def _get_angel_service(user: User):
    if not user.angel_one_api_key:
        return None
    from app.services.angel_one import get_angel_one_service
    return get_angel_one_service(
        user.id, user.angel_one_api_key,
        user.angel_one_client_id, user.angel_one_password,
        user.angel_one_totp_secret
    )


@router.get("/sync")
async def sync_portfolio(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync portfolio data from Angel One."""
    angel = _get_angel_service(current_user)
    if not angel:
        raise HTTPException(status_code=400, detail="Angel One connection required")

    # Get or create portfolio
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == current_user.id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        portfolio = Portfolio(user_id=current_user.id)
        db.add(portfolio)
        await db.flush()

    # Sync holdings
    raw_holdings = await angel.get_holdings()
    if raw_holdings:
        # Clear existing and recreate
        existing = await db.execute(select(Holding).where(Holding.portfolio_id == portfolio.id))
        for h in existing.scalars():
            await db.delete(h)
        await db.flush()

        total_investment = 0
        total_current = 0
        for h in raw_holdings:
            qty = int(h.get("quantity", 0))
            avg = float(h.get("averageprice", 0))
            ltp = float(h.get("ltp", avg))
            pnl = (ltp - avg) * qty
            pnl_pct = ((ltp - avg) / avg * 100) if avg else 0

            holding = Holding(
                portfolio_id=portfolio.id,
                symbol=h.get("tradingsymbol", ""),
                exchange=h.get("exchange", "NSE"),
                isin=h.get("isin", ""),
                quantity=qty,
                avg_buy_price=avg,
                current_price=ltp,
                current_value=ltp * qty,
                pnl=pnl,
                pnl_percent=round(pnl_pct, 2),
            )
            db.add(holding)
            total_investment += avg * qty
            total_current += ltp * qty

        portfolio.total_investment = total_investment
        portfolio.current_value = total_current
        portfolio.unrealized_pnl = total_current - total_investment

    # Sync positions
    raw_positions = await angel.get_positions()
    if raw_positions:
        existing_pos = await db.execute(select(Position).where(Position.portfolio_id == portfolio.id))
        for p in existing_pos.scalars():
            await db.delete(p)
        await db.flush()

        today_pnl = 0
        for p in raw_positions:
            pnl = float(p.get("pnl", 0))
            pos = Position(
                portfolio_id=portfolio.id,
                symbol=p.get("tradingsymbol", ""),
                exchange=p.get("exchange", "NSE"),
                product_type=p.get("producttype", "INTRADAY"),
                quantity=int(p.get("netqty", 0)),
                buy_qty=int(p.get("buyqty", 0)),
                sell_qty=int(p.get("sellqty", 0)),
                avg_buy_price=float(p.get("buyavgprice", 0)),
                avg_sell_price=float(p.get("sellavgprice", 0)),
                current_price=float(p.get("ltp", 0)),
                pnl=pnl,
                unrealized_pnl=float(p.get("unrealisedpnl", pnl)),
                is_open=int(p.get("netqty", 0)) != 0,
            )
            db.add(pos)
            today_pnl += pnl

        portfolio.today_pnl = today_pnl

    # Sync margin
    margin_data = await angel.get_rms_data()
    if margin_data:
        portfolio.available_margin = float(margin_data.get("net", 0) or 0)
        portfolio.used_margin = float(margin_data.get("utilisedAmount", 0) or 0)

    portfolio.last_synced = datetime.utcnow()
    portfolio.total_pnl = (portfolio.unrealized_pnl or 0) + (portfolio.today_pnl or 0)
    db.add(portfolio)
    await db.commit()

    return {"status": "synced", "last_synced": portfolio.last_synced.isoformat()}


@router.get("/overview")
async def get_portfolio_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == current_user.id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return {"total_investment": 0, "current_value": 0, "total_pnl": 0}

    return {
        "total_investment": portfolio.total_investment,
        "current_value": portfolio.current_value,
        "available_margin": portfolio.available_margin,
        "used_margin": portfolio.used_margin,
        "total_pnl": portfolio.total_pnl,
        "realized_pnl": portfolio.realized_pnl,
        "unrealized_pnl": portfolio.unrealized_pnl,
        "today_pnl": portfolio.today_pnl,
        "last_synced": portfolio.last_synced.isoformat() if portfolio.last_synced else None,
    }


@router.get("/holdings")
async def get_holdings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == current_user.id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return []
    h_result = await db.execute(select(Holding).where(Holding.portfolio_id == portfolio.id))
    return h_result.scalars().all()


@router.get("/positions")
async def get_positions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == current_user.id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return []
    p_result = await db.execute(select(Position).where(Position.portfolio_id == portfolio.id, Position.is_open == True))
    return p_result.scalars().all()
