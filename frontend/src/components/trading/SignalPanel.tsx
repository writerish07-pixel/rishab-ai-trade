'use client';

import { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/store';
import { scanMarket } from '@/store/signalSlice';
import { setSelectedSymbol } from '@/store/marketSlice';
import { Signal } from '@/types';
import {
  TrendingUp, TrendingDown, Target, ShieldAlert,
  Zap, RefreshCw, BarChart2
} from 'lucide-react';
import toast from 'react-hot-toast';
import { ordersAPI } from '@/services/api';

function SignalCard({ signal, onTrade }: { signal: Signal; onTrade: (signal: Signal, side: 'BUY' | 'SELL') => void }) {
  const isBuy = signal.signal_type === 'BUY';
  const confidence = Math.round(signal.confidence * 100);

  return (
    <div className={`card border transition-all hover:border-accent-blue/50 animate-slide-up ${
      isBuy ? 'border-bull/20' : 'border-bear/20'
    }`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            {isBuy
              ? <TrendingUp className="w-4 h-4 text-bull" />
              : <TrendingDown className="w-4 h-4 text-bear" />
            }
            <span className="font-bold text-text-primary">{signal.symbol}</span>
            <span className="text-xs text-text-muted">{signal.exchange}</span>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className={`badge ${
              signal.strength === 'STRONG' ? 'badge-bull' :
              signal.strength === 'MODERATE' ? 'badge-neutral' : 'badge-blue'
            }`}>{signal.strength}</span>
            {signal.pattern_detected && (
              <span className="badge badge-blue text-[10px]">
                {signal.pattern_detected.replace(/_/g, ' ')}
              </span>
            )}
            {signal.volume_spike && (
              <span className="badge bg-purple-900/40 text-purple-300">VOL SPIKE</span>
            )}
          </div>
        </div>

        {/* Confidence */}
        <div className="text-right">
          <div className={`text-2xl font-bold font-trading ${
            confidence >= 75 ? 'text-bull' : confidence >= 65 ? 'text-yellow-400' : 'text-bear'
          }`}>{confidence}%</div>
          <div className="text-xs text-text-muted">Confidence</div>
        </div>
      </div>

      {/* Price levels */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="bg-bg-secondary rounded-lg p-2 border border-border">
          <div className="text-xs text-text-muted mb-0.5">Entry</div>
          <div className="font-trading font-bold text-text-primary text-sm">
            ₹{signal.entry_price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </div>
        </div>
        <div className="bg-red-950/20 rounded-lg p-2 border border-bear/20">
          <div className="flex items-center gap-1 text-xs text-text-muted mb-0.5">
            <ShieldAlert className="w-3 h-3 text-bear" /> Stop Loss
          </div>
          <div className="font-trading font-bold text-bear text-sm">
            ₹{signal.stop_loss.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </div>
        </div>
        <div className="bg-green-950/20 rounded-lg p-2 border border-bull/20">
          <div className="flex items-center gap-1 text-xs text-text-muted mb-0.5">
            <Target className="w-3 h-3 text-bull" /> Target 1
          </div>
          <div className="font-trading font-bold text-bull text-sm">
            ₹{signal.target_1.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </div>
        </div>
        <div className="bg-bg-secondary rounded-lg p-2 border border-border">
          <div className="text-xs text-text-muted mb-0.5">R:R Ratio</div>
          <div className="font-trading font-bold text-text-primary text-sm">
            1:{signal.risk_reward_ratio}
          </div>
        </div>
      </div>

      {/* Indicators row */}
      <div className="flex flex-wrap gap-2 mb-3 text-xs font-trading">
        {signal.rsi !== undefined && signal.rsi !== null && (
          <span className={`px-2 py-0.5 rounded-full ${
            signal.rsi < 35 ? 'bg-green-900/40 text-bull' :
            signal.rsi > 65 ? 'bg-red-900/40 text-bear' :
            'bg-bg-secondary text-text-muted'
          }`}>RSI {signal.rsi?.toFixed(1)}</span>
        )}
        {signal.macd !== undefined && (
          <span className={`px-2 py-0.5 rounded-full ${
            (signal.macd || 0) > 0 ? 'bg-green-900/40 text-bull' : 'bg-red-900/40 text-bear'
          }`}>MACD {signal.macd?.toFixed(2)}</span>
        )}
        {signal.vwap && (
          <span className="px-2 py-0.5 rounded-full bg-bg-secondary text-text-muted">
            VWAP {signal.vwap.toFixed(2)}
          </span>
        )}
        {signal.trend && (
          <span className={`px-2 py-0.5 rounded-full ${
            signal.trend === 'BULLISH' ? 'bg-green-900/40 text-bull' :
            signal.trend === 'BEARISH' ? 'bg-red-900/40 text-bear' :
            'bg-yellow-900/40 text-yellow-400'
          }`}>{signal.trend}</span>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={() => onTrade(signal, isBuy ? 'BUY' : 'SELL')}
          className={`flex-1 py-2 rounded-lg font-bold text-sm transition-colors ${
            isBuy
              ? 'bg-bull/10 text-bull border border-bull/30 hover:bg-bull hover:text-white'
              : 'bg-bear/10 text-bear border border-bear/30 hover:bg-bear hover:text-white'
          }`}
        >
          Execute {signal.signal_type}
        </button>
        <button className="px-3 py-2 rounded-lg border border-border text-text-muted hover:text-text-primary transition-colors text-sm">
          <BarChart2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

export function SignalPanel() {
  const dispatch = useAppDispatch();
  const { activeSignals, scanning, marketSentiment, niftyTrend, bankNiftyTrend } =
    useAppSelector((state) => state.signals);

  useEffect(() => {
    dispatch(scanMarket({ limit: 15 }));
  }, [dispatch]);

  const handleTrade = async (signal: Signal, side: 'BUY' | 'SELL') => {
    try {
      const result = await ordersAPI.placeOrder({
        symbol: signal.symbol,
        exchange: signal.exchange as any,
        order_type: 'MARKET',
        order_side: side,
        product_type: 'INTRADAY',
        quantity: 1,
        signal_id: signal.id,
      });
      toast.success(`${side} order placed for ${signal.symbol}! ID: ${result.order_id}`);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Order failed');
    }
  };

  const handleSelectSignal = (signal: Signal) => {
    dispatch(setSelectedSymbol(signal.symbol));
  };

  return (
    <div className="space-y-4">
      {/* Market sentiment bar */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Market', value: marketSentiment },
          { label: 'NIFTY', value: niftyTrend },
          { label: 'BANK NIFTY', value: bankNiftyTrend },
        ].map(({ label, value }) => (
          <div key={label} className="card text-center">
            <div className="text-xs text-text-muted mb-1">{label}</div>
            <div className={`text-sm font-bold ${
              value === 'BULLISH' ? 'text-bull' :
              value === 'BEARISH' ? 'text-bear' : 'text-yellow-400'
            }`}>{value}</div>
          </div>
        ))}
      </div>

      {/* Scan button */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text-primary">
          AI Signals <span className="text-text-muted font-normal">({activeSignals.length} found)</span>
        </h3>
        <button
          onClick={() => dispatch(scanMarket({ limit: 15 }))}
          disabled={scanning}
          className="btn-ghost text-xs flex items-center gap-1.5 py-1.5 px-3"
        >
          {scanning
            ? <Zap className="w-3.5 h-3.5 animate-pulse text-accent-blue" />
            : <RefreshCw className="w-3.5 h-3.5" />
          }
          {scanning ? 'Scanning...' : 'Scan Market'}
        </button>
      </div>

      {/* Signal cards */}
      {scanning && activeSignals.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 gap-3">
          <Zap className="w-8 h-8 text-accent-blue animate-pulse" />
          <p className="text-text-secondary text-sm">Scanning Nifty 50 for opportunities...</p>
        </div>
      ) : activeSignals.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 gap-3">
          <BarChart2 className="w-8 h-8 text-text-muted" />
          <p className="text-text-secondary text-sm">No high-confidence signals at the moment</p>
          <p className="text-text-muted text-xs">Market conditions must align. Click Scan Market to check.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {activeSignals.map((signal, idx) => (
            <div key={`${signal.symbol}-${idx}`} onClick={() => handleSelectSignal(signal)}>
              <SignalCard signal={signal} onTrade={handleTrade} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
