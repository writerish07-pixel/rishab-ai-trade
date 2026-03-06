'use client';

import { useAppSelector } from '@/store';
import { QuoteData } from '@/types';

function IndexTicker({ quote, label }: { quote: QuoteData | undefined; label: string }) {
  if (!quote) return (
    <div className="flex items-center gap-3">
      <span className="text-text-muted text-xs font-medium">{label}</span>
      <span className="text-text-muted text-xs">Loading...</span>
    </div>
  );

  const isPositive = quote.change >= 0;
  return (
    <div className="flex items-center gap-2 border-r border-border pr-4">
      <span className="text-text-secondary text-xs font-medium">{label}</span>
      <span className="font-trading text-sm font-semibold text-text-primary">
        {quote.ltp.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
      </span>
      <span className={`text-xs font-medium font-trading ${isPositive ? 'text-bull' : 'text-bear'}`}>
        {isPositive ? '+' : ''}{quote.change.toFixed(2)} ({isPositive ? '+' : ''}{quote.change_percent.toFixed(2)}%)
      </span>
    </div>
  );
}

export function MarketOverviewBar() {
  const quotes = useAppSelector((state) => state.market.quotes);
  const overview = useAppSelector((state) => state.market.overview);

  return (
    <div className="h-9 bg-bg-secondary border-b border-border flex items-center px-4 gap-4 overflow-x-auto flex-shrink-0">
      <IndexTicker quote={quotes['NIFTY50'] || overview?.nifty50} label="NIFTY 50" />
      <IndexTicker quote={quotes['BANKNIFTY'] || overview?.bank_nifty} label="BANK NIFTY" />
      <IndexTicker quote={quotes['SENSEX'] || overview?.sensex} label="SENSEX" />

      {overview && (
        <>
          <div className="border-r border-border pr-4 flex items-center gap-2">
            <span className="text-text-muted text-xs">A/D</span>
            <span className={`text-xs font-medium font-trading ${
              overview.advance_decline_ratio > 1 ? 'text-bull' : 'text-bear'
            }`}>
              {overview.advance_decline_ratio.toFixed(2)}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-text-muted text-xs">Breadth</span>
            <span className={`text-xs font-medium badge ${
              overview.market_breadth === 'POSITIVE' ? 'badge-bull' :
              overview.market_breadth === 'NEGATIVE' ? 'badge-bear' : 'badge-neutral'
            }`}>
              {overview.market_breadth}
            </span>
          </div>
        </>
      )}
    </div>
  );
}
