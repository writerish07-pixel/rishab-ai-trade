import { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/store';
import { fetchMarketOverview, fetchMarketStatus, fetchCandles, setSelectedSymbol } from '@/store/marketSlice';
import { useWebSocket } from './useWebSocket';

export function useMarketData() {
  const dispatch = useAppDispatch();
  const { subscribe } = useWebSocket();
  const { overview, quotes, candles, watchlist, selectedSymbol, marketStatus, loading } =
    useAppSelector((state) => state.market);

  useEffect(() => {
    dispatch(fetchMarketStatus());
    dispatch(fetchMarketOverview());
  }, [dispatch]);

  // Subscribe to all watchlist symbols via WebSocket
  useEffect(() => {
    const symbols = watchlist.map((w) => w.symbol);
    if (symbols.length > 0) {
      subscribe(symbols);
    }
  }, [watchlist, subscribe]);

  // Refresh overview every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      dispatch(fetchMarketOverview());
    }, 30000);
    return () => clearInterval(interval);
  }, [dispatch]);

  const selectSymbol = (symbol: string) => {
    dispatch(setSelectedSymbol(symbol));
    subscribe([symbol]);
  };

  const loadCandles = (symbol: string, exchange = 'NSE', interval = '5m', days = 3) => {
    dispatch(fetchCandles({ symbol, exchange, interval, days }));
  };

  return {
    overview,
    quotes,
    candles,
    watchlist,
    selectedSymbol,
    marketStatus,
    loading,
    selectSymbol,
    loadCandles,
    selectedQuote: quotes[selectedSymbol],
    selectedCandles: candles[selectedSymbol] || [],
  };
}
