'use client';

import { useState } from 'react';
import { Plus, Search, X } from 'lucide-react';
import { useAppSelector, useAppDispatch } from '@/store';
import { addToWatchlist, removeFromWatchlist } from '@/store/marketSlice';
import { marketAPI } from '@/services/api';
import { WatchlistItem } from '@/types';
import toast from 'react-hot-toast';

interface Props {
  onSelect: (symbol: string) => void;
  selectedSymbol: string;
}

export function Watchlist({ onSelect, selectedSymbol }: Props) {
  const dispatch = useAppDispatch();
  const { watchlist, quotes } = useAppSelector((state) => state.market);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);

  const handleSearch = async (q: string) => {
    setSearchQuery(q);
    if (q.length < 2) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const results = await marketAPI.searchSymbol(q);
      setSearchResults(results.slice(0, 6));
    } catch {
      // silent
    } finally {
      setSearching(false);
    }
  };

  const handleAdd = (item: any) => {
    const wl: WatchlistItem = {
      symbol: item.tradingsymbol || item.symbol,
      exchange: 'NSE',
      token: item.symboltoken,
    };
    dispatch(addToWatchlist(wl));
    onSelect(wl.symbol);
    setSearchQuery('');
    setSearchResults([]);
    toast.success(`${wl.symbol} added to watchlist`);
  };

  const handleRemove = (e: React.MouseEvent, symbol: string) => {
    e.stopPropagation();
    dispatch(removeFromWatchlist(symbol));
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-3 border-b border-border">
        <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">
          Watchlist
        </h3>
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted" />
          <input
            type="text"
            placeholder="Add symbol..."
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            className="input pl-8 text-xs py-1.5"
          />
        </div>
        {/* Search results dropdown */}
        {searchResults.length > 0 && (
          <div className="absolute z-50 mt-1 w-56 bg-bg-card border border-border rounded-lg overflow-hidden shadow-xl">
            {searchResults.map((r) => (
              <button
                key={r.symboltoken}
                onClick={() => handleAdd(r)}
                className="w-full flex items-center justify-between px-3 py-2 hover:bg-bg-hover text-left text-xs transition-colors"
              >
                <div>
                  <div className="text-text-primary font-medium">{r.tradingsymbol}</div>
                  <div className="text-text-muted">{r.name || r.exchange}</div>
                </div>
                <Plus className="w-3.5 h-3.5 text-text-muted" />
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Watchlist items */}
      <div className="flex-1 overflow-y-auto">
        {watchlist.map((item) => {
          const quote = quotes[item.symbol] || item.quote;
          const isSelected = selectedSymbol === item.symbol;
          const isPositive = (quote?.change ?? 0) >= 0;

          return (
            <div
              key={item.symbol}
              onClick={() => onSelect(item.symbol)}
              className={`px-3 py-2.5 cursor-pointer group transition-colors border-l-2 ${
                isSelected
                  ? 'bg-bg-hover border-l-accent-blue'
                  : 'border-l-transparent hover:bg-bg-hover'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-semibold text-text-primary truncate">
                      {item.symbol}
                    </span>
                    <span className="text-[10px] text-text-muted">{item.exchange}</span>
                  </div>
                  {quote && (
                    <div className="font-trading text-sm font-bold text-text-primary mt-0.5">
                      {quote.ltp.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                    </div>
                  )}
                </div>
                <div className="flex flex-col items-end gap-1">
                  <button
                    onClick={(e) => handleRemove(e, item.symbol)}
                    className="opacity-0 group-hover:opacity-100 p-0.5 text-text-muted hover:text-bear transition-all"
                  >
                    <X className="w-3 h-3" />
                  </button>
                  {quote && (
                    <span className={`font-trading text-xs font-medium ${
                      isPositive ? 'text-bull' : 'text-bear'
                    }`}>
                      {isPositive ? '+' : ''}{quote.change_percent.toFixed(2)}%
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
