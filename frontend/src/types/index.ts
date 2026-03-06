// ============================================
// Core Trading Types
// ============================================

export interface QuoteData {
  symbol: string;
  exchange: string;
  ltp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  change: number;
  change_percent: number;
  volume: number;
  avg_price: number;
  upper_circuit?: number;
  lower_circuit?: number;
  bid?: number;
  ask?: number;
  timestamp: string;
}

export interface OHLCData {
  symbol: string;
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Signal {
  id?: number;
  symbol: string;
  exchange: string;
  signal_type: 'BUY' | 'SELL' | 'HOLD';
  strength: 'STRONG' | 'MODERATE' | 'WEAK';
  confidence: number;
  entry_price: number;
  stop_loss: number;
  target_1: number;
  target_2?: number;
  target_3?: number;
  risk_reward_ratio: number;
  rsi?: number;
  macd?: number;
  vwap?: number;
  ema_9?: number;
  ema_21?: number;
  ema_50?: number;
  adx?: number;
  volume_spike: boolean;
  pattern_detected?: string;
  trend?: string;
  reasons?: { buy: string[]; sell: string[] };
  institutional_signal?: string;
  generated_at?: string;
  created_at?: string;
}

export type OrderSide = 'BUY' | 'SELL';
export type OrderType = 'MARKET' | 'LIMIT' | 'STOP_LOSS' | 'STOP_LOSS_MARKET' | 'BRACKET';
export type ProductType = 'INTRADAY' | 'DELIVERY' | 'FUTURES' | 'OPTIONS';
export type Exchange = 'NSE' | 'BSE' | 'NFO' | 'BFO' | 'MCX';

export interface PlaceOrderRequest {
  symbol: string;
  exchange: Exchange;
  order_type: OrderType;
  order_side: OrderSide;
  product_type: ProductType;
  quantity: number;
  price?: number;
  trigger_price?: number;
  square_off?: number;
  stoploss?: number;
  signal_id?: number;
}

export interface Trade {
  id: number;
  symbol: string;
  exchange: string;
  order_type: string;
  order_side: string;
  product_type: string;
  quantity: number;
  price: number;
  status: string;
  angel_one_order_id?: string;
  executed_price: number;
  executed_qty: number;
  pnl: number;
  is_algo_order: boolean;
  created_at: string;
}

export interface Holding {
  id: number;
  symbol: string;
  exchange: string;
  isin?: string;
  quantity: number;
  avg_buy_price: number;
  current_price: number;
  current_value: number;
  pnl: number;
  pnl_percent: number;
}

export interface Position {
  id: number;
  symbol: string;
  exchange: string;
  product_type: string;
  quantity: number;
  buy_qty: number;
  sell_qty: number;
  avg_buy_price: number;
  avg_sell_price: number;
  current_price: number;
  pnl: number;
  unrealized_pnl: number;
  is_open: boolean;
}

export interface PortfolioOverview {
  total_investment: number;
  current_value: number;
  available_margin: number;
  used_margin: number;
  total_pnl: number;
  realized_pnl: number;
  unrealized_pnl: number;
  today_pnl: number;
  last_synced?: string;
}

export interface MarketOverview {
  nifty50: QuoteData;
  bank_nifty: QuoteData;
  sensex: QuoteData;
  top_gainers: TopMover[];
  top_losers: TopMover[];
  most_active: TopMover[];
  advance_decline_ratio: number;
  market_breadth: string;
}

export interface TopMover {
  symbol: string;
  ltp: number;
  change: number;
  change_percent: number;
  volume: number;
  sector?: string;
}

export interface User {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  is_admin: boolean;
  angel_one_client_id?: string;
  created_at: string;
}

// WebSocket message types
export type WSMessageType =
  | 'price_update'
  | 'signal_alert'
  | 'connected'
  | 'subscribed'
  | 'heartbeat'
  | 'pong'
  | 'error';

export interface WSMessage {
  type: WSMessageType;
  data?: any;
  message?: string;
  symbols?: string[];
}

export interface WatchlistItem {
  symbol: string;
  exchange: Exchange;
  token?: string;
  quote?: QuoteData;
}
