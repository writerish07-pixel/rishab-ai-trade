'use client';

import { Signal } from '@/types';
import { TrendingUp, TrendingDown, Target, ShieldAlert } from 'lucide-react';

interface Props {
  signal: Signal;
}

export function SignalOverlay({ signal }: Props) {
  const isBuy = signal.signal_type === 'BUY';
  const confidence = Math.round(signal.confidence * 100);

  return (
    <div className={`rounded-xl border p-3 ${
      isBuy ? 'bg-green-950/30 border-bull/30' : 'bg-red-950/30 border-bear/30'
    }`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {isBuy
            ? <TrendingUp className="w-4 h-4 text-bull" />
            : <TrendingDown className="w-4 h-4 text-bear" />
          }
          <span className={`text-sm font-bold ${isBuy ? 'text-bull' : 'text-bear'}`}>
            {signal.signal_type} SIGNAL — {signal.symbol}
          </span>
          <span className={`badge ${
            signal.strength === 'STRONG' ? 'badge-bull' :
            signal.strength === 'MODERATE' ? 'badge-neutral' : 'badge-blue'
          }`}>
            {signal.strength}
          </span>
        </div>

        <div className="flex items-center gap-3 text-xs">
          {/* Confidence gauge */}
          <div className="flex items-center gap-1.5">
            <span className="text-text-muted">Confidence</span>
            <div className="w-24 h-2 bg-bg-secondary rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${
                  confidence >= 75 ? 'bg-bull' : confidence >= 65 ? 'bg-yellow-400' : 'bg-bear'
                }`}
                style={{ width: `${confidence}%` }}
              />
            </div>
            <span className={`font-trading font-bold ${
              confidence >= 75 ? 'text-bull' : confidence >= 65 ? 'text-yellow-400' : 'text-bear'
            }`}>{confidence}%</span>
          </div>

          <span className="text-text-muted">R:R</span>
          <span className="font-trading font-bold text-text-primary">1:{signal.risk_reward_ratio}</span>
        </div>
      </div>

      {/* Levels */}
      <div className="flex items-center gap-4 text-xs font-trading flex-wrap">
        <div className="flex items-center gap-1.5">
          <span className="text-text-muted">Entry</span>
          <span className="font-bold text-text-primary">
            ₹{signal.entry_price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <ShieldAlert className="w-3.5 h-3.5 text-bear" />
          <span className="text-text-muted">SL</span>
          <span className="font-bold text-bear">
            ₹{signal.stop_loss.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <Target className="w-3.5 h-3.5 text-bull" />
          <span className="text-text-muted">T1</span>
          <span className="font-bold text-bull">
            ₹{signal.target_1.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </span>
        </div>
        {signal.target_2 && (
          <div className="flex items-center gap-1.5">
            <span className="text-text-muted">T2</span>
            <span className="font-bold text-bull">
              ₹{signal.target_2.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
            </span>
          </div>
        )}
        {signal.pattern_detected && (
          <div className="flex items-center gap-1.5">
            <span className="text-text-muted">Pattern</span>
            <span className="badge badge-blue">{signal.pattern_detected.replace(/_/g, ' ')}</span>
          </div>
        )}
        {signal.trend && (
          <div className="flex items-center gap-1.5">
            <span className="text-text-muted">Trend</span>
            <span className={`badge ${
              signal.trend === 'BULLISH' ? 'badge-bull' :
              signal.trend === 'BEARISH' ? 'badge-bear' : 'badge-neutral'
            }`}>{signal.trend}</span>
          </div>
        )}
      </div>

      {/* Reasons */}
      {signal.reasons && (
        <div className="mt-2 pt-2 border-t border-border/50">
          <div className="flex flex-wrap gap-1.5">
            {(isBuy ? signal.reasons.buy : signal.reasons.sell)?.slice(0, 5).map((r, i) => (
              <span key={i} className={`text-[10px] px-2 py-0.5 rounded-full ${
                isBuy ? 'bg-green-900/40 text-green-300' : 'bg-red-900/40 text-red-300'
              }`}>{r}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
