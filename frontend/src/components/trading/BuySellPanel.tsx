'use client';

import { useState } from 'react';
import { TrendingUp, TrendingDown, AlertCircle, Loader2 } from 'lucide-react';
import { ordersAPI } from '@/services/api';
import { useAppSelector } from '@/store';
import { OrderType, ProductType, Exchange } from '@/types';
import toast from 'react-hot-toast';

interface Props {
  symbol: string;
}

type OrderSide = 'BUY' | 'SELL';

export function BuySellPanel({ symbol }: Props) {
  const quote = useAppSelector((state) => state.market.quotes[symbol]);
  const currentSignal = useAppSelector((state) =>
    state.signals.activeSignals.find((s) => s.symbol === symbol) || state.signals.currentAnalysis
  );

  const [side, setSide] = useState<OrderSide>('BUY');
  const [orderType, setOrderType] = useState<OrderType>('MARKET');
  const [productType, setProductType] = useState<ProductType>('INTRADAY');
  const [quantity, setQuantity] = useState(1);
  const [price, setPrice] = useState('');
  const [triggerPrice, setTriggerPrice] = useState('');
  const [stopLoss, setStopLoss] = useState('');
  const [target, setTarget] = useState('');
  const [loading, setLoading] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  // Pre-fill from signal
  const fillFromSignal = () => {
    if (!currentSignal) return;
    setSide(currentSignal.signal_type === 'BUY' ? 'BUY' : 'SELL');
    setPrice(currentSignal.entry_price.toString());
    setStopLoss(currentSignal.stop_loss.toString());
    setTarget(currentSignal.target_1.toString());
    toast.success('Signal levels applied');
  };

  const handleSubmit = async () => {
    setShowConfirm(false);
    setLoading(true);
    try {
      const order = {
        symbol,
        exchange: 'NSE' as Exchange,
        order_type: orderType,
        order_side: side,
        product_type: productType,
        quantity,
        price: orderType !== 'MARKET' ? parseFloat(price) || 0 : 0,
        trigger_price: parseFloat(triggerPrice) || 0,
        stoploss: parseFloat(stopLoss) || 0,
        square_off: parseFloat(target) || 0,
        signal_id: currentSignal?.id,
      };

      const result = await ordersAPI.placeOrder(order);
      toast.success(`${side} order placed! ID: ${result.order_id}`);
    } catch (error: any) {
      const msg = error?.response?.data?.detail || 'Order failed';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const estimatedValue = quote ? (quote.ltp * quantity).toLocaleString('en-IN', { maximumFractionDigits: 2 }) : '—';

  return (
    <div className="p-4 flex flex-col gap-4">
      <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wider">
        Place Order
      </h3>

      {/* Symbol + LTP */}
      <div className="bg-bg-secondary rounded-xl p-3 border border-border">
        <div className="flex items-center justify-between">
          <span className="text-sm font-bold text-text-primary">{symbol}</span>
          {quote && (
            <div className="text-right">
              <div className="font-trading text-lg font-bold text-text-primary">
                ₹{quote.ltp.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
              </div>
              <div className={`font-trading text-xs ${quote.change >= 0 ? 'text-bull' : 'text-bear'}`}>
                {quote.change >= 0 ? '+' : ''}{quote.change.toFixed(2)} ({quote.change_percent.toFixed(2)}%)
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Signal quick fill */}
      {currentSignal && currentSignal.symbol === symbol && (
        <button
          onClick={fillFromSignal}
          className="flex items-center justify-center gap-2 text-xs py-2 px-3 bg-accent-blue/10 text-accent-blue border border-accent-blue/30 rounded-lg hover:bg-accent-blue/20 transition-colors"
        >
          <AlertCircle className="w-3.5 h-3.5" />
          Apply AI Signal Levels
        </button>
      )}

      {/* BUY / SELL toggle */}
      <div className="flex rounded-xl overflow-hidden border border-border">
        <button
          onClick={() => setSide('BUY')}
          className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-bold transition-colors ${
            side === 'BUY'
              ? 'bg-bull text-white'
              : 'bg-bg-secondary text-text-muted hover:text-text-primary'
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          BUY
        </button>
        <button
          onClick={() => setSide('SELL')}
          className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-bold transition-colors ${
            side === 'SELL'
              ? 'bg-bear text-white'
              : 'bg-bg-secondary text-text-muted hover:text-text-primary'
          }`}
        >
          <TrendingDown className="w-4 h-4" />
          SELL
        </button>
      </div>

      {/* Product type */}
      <div>
        <label className="text-xs text-text-muted mb-1.5 block">Product Type</label>
        <div className="grid grid-cols-2 gap-1">
          {(['INTRADAY', 'DELIVERY', 'FUTURES', 'OPTIONS'] as ProductType[]).map((pt) => (
            <button
              key={pt}
              onClick={() => setProductType(pt)}
              className={`py-1.5 text-xs rounded-lg border transition-colors ${
                productType === pt
                  ? 'border-accent-blue bg-accent-blue/10 text-accent-blue'
                  : 'border-border text-text-muted hover:text-text-primary'
              }`}
            >
              {pt}
            </button>
          ))}
        </div>
      </div>

      {/* Order type */}
      <div>
        <label className="text-xs text-text-muted mb-1.5 block">Order Type</label>
        <div className="grid grid-cols-2 gap-1">
          {(['MARKET', 'LIMIT', 'STOP_LOSS', 'BRACKET'] as OrderType[]).map((ot) => (
            <button
              key={ot}
              onClick={() => setOrderType(ot)}
              className={`py-1.5 text-xs rounded-lg border transition-colors ${
                orderType === ot
                  ? 'border-accent-blue bg-accent-blue/10 text-accent-blue'
                  : 'border-border text-text-muted hover:text-text-primary'
              }`}
            >
              {ot.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Quantity */}
      <div>
        <label className="text-xs text-text-muted mb-1.5 block">Quantity (Shares)</label>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setQuantity(Math.max(1, quantity - 1))}
            className="w-8 h-8 border border-border rounded-lg text-text-secondary hover:text-text-primary hover:border-accent-blue transition-colors font-bold"
          >
            −
          </button>
          <input
            type="number"
            min={1}
            value={quantity}
            onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
            className="input text-center font-trading font-bold"
          />
          <button
            onClick={() => setQuantity(quantity + 1)}
            className="w-8 h-8 border border-border rounded-lg text-text-secondary hover:text-text-primary hover:border-accent-blue transition-colors font-bold"
          >
            +
          </button>
        </div>
      </div>

      {/* Price fields (for non-market orders) */}
      {orderType !== 'MARKET' && (
        <div>
          <label className="text-xs text-text-muted mb-1.5 block">Price (₹)</label>
          <input
            type="number"
            className="input font-trading"
            placeholder="0.00"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
          />
        </div>
      )}

      {(orderType === 'STOP_LOSS' || orderType === 'BRACKET') && (
        <div>
          <label className="text-xs text-text-muted mb-1.5 block">Trigger Price (₹)</label>
          <input
            type="number"
            className="input font-trading"
            placeholder="0.00"
            value={triggerPrice}
            onChange={(e) => setTriggerPrice(e.target.value)}
          />
        </div>
      )}

      {orderType === 'BRACKET' && (
        <>
          <div>
            <label className="text-xs text-text-muted mb-1.5 block">Stop Loss (₹)</label>
            <input
              type="number"
              className="input font-trading border-bear/30 focus:border-bear"
              placeholder="0.00"
              value={stopLoss}
              onChange={(e) => setStopLoss(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs text-text-muted mb-1.5 block">Target (₹)</label>
            <input
              type="number"
              className="input font-trading border-bull/30 focus:border-bull"
              placeholder="0.00"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            />
          </div>
        </>
      )}

      {/* Estimated value */}
      <div className="flex items-center justify-between text-xs border-t border-border pt-3">
        <span className="text-text-muted">Est. Value</span>
        <span className="font-trading font-bold text-text-primary">₹{estimatedValue}</span>
      </div>

      {/* Submit button */}
      {!showConfirm ? (
        <button
          onClick={() => setShowConfirm(true)}
          disabled={loading}
          className={`w-full py-3.5 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all ${
            side === 'BUY'
              ? 'bg-bull hover:bg-green-400 text-white'
              : 'bg-bear hover:bg-red-400 text-white'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {side === 'BUY' ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
          {side} {quantity} {symbol}
        </button>
      ) : (
        <div className="space-y-2">
          <div className="text-xs text-center text-text-secondary bg-bg-secondary rounded-lg p-2 border border-border">
            Confirm {side} {quantity} × {symbol} @ {orderType === 'MARKET' ? 'Market' : `₹${price}`}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowConfirm(false)}
              className="flex-1 btn-ghost text-sm py-2.5"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={loading}
              className={`flex-1 py-2.5 rounded-xl font-bold text-sm flex items-center justify-center gap-2 ${
                side === 'BUY' ? 'bg-bull text-white' : 'bg-bear text-white'
              } disabled:opacity-50`}
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              Confirm {side}
            </button>
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <p className="text-[10px] text-text-muted text-center leading-relaxed">
        Orders execute via Angel One SmartAPI in real-time. Verify before confirming.
      </p>
    </div>
  );
}
