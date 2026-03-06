from typing import Optional, List
from pydantic import BaseModel


class QuoteData(BaseModel):
    symbol: str
    exchange: str
    ltp: float             # Last traded price
    open: float
    high: float
    low: float
    close: float
    change: float
    change_percent: float
    volume: int
    avg_price: float
    upper_circuit: Optional[float] = None
    lower_circuit: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    timestamp: str


class OHLCData(BaseModel):
    symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class MarketStatus(BaseModel):
    is_open: bool
    status: str
    session: str
    next_open: Optional[str] = None
    next_close: Optional[str] = None


class OptionChainEntry(BaseModel):
    strike_price: float
    ce_oi: int
    ce_change_oi: int
    ce_volume: int
    ce_iv: float
    ce_ltp: float
    ce_bid: float
    ce_ask: float
    pe_oi: int
    pe_change_oi: int
    pe_volume: int
    pe_iv: float
    pe_ltp: float
    pe_bid: float
    pe_ask: float


class OptionChainResponse(BaseModel):
    symbol: str
    expiry_date: str
    spot_price: float
    atm_strike: float
    pcr_ratio: float
    total_ce_oi: int
    total_pe_oi: int
    chain: List[OptionChainEntry]


class InstitutionalActivity(BaseModel):
    symbol: str
    bulk_deal_qty: int
    block_deal_qty: int
    delivery_volume: float
    delivery_percent: float
    fii_activity: str    # BUYING / SELLING / NEUTRAL
    dii_activity: str
    signal: str          # ACCUMULATION / DISTRIBUTION / NEUTRAL


class TopMover(BaseModel):
    symbol: str
    ltp: float
    change: float
    change_percent: float
    volume: int
    sector: Optional[str] = None


class MarketOverview(BaseModel):
    nifty50: QuoteData
    bank_nifty: QuoteData
    sensex: QuoteData
    top_gainers: List[TopMover]
    top_losers: List[TopMover]
    most_active: List[TopMover]
    advance_decline_ratio: float
    market_breadth: str   # POSITIVE / NEGATIVE / NEUTRAL
