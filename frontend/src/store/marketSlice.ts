import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { QuoteData, OHLCData, MarketOverview, WatchlistItem } from '@/types';
import { marketAPI } from '@/services/api';

interface MarketState {
  overview: MarketOverview | null;
  quotes: Record<string, QuoteData>;
  candles: Record<string, OHLCData[]>;
  watchlist: WatchlistItem[];
  selectedSymbol: string;
  marketStatus: { is_open: boolean; status: string; session: string } | null;
  loading: boolean;
  error: string | null;
}

const DEFAULT_WATCHLIST: WatchlistItem[] = [
  { symbol: 'NIFTY50', exchange: 'NSE' },
  { symbol: 'BANKNIFTY', exchange: 'NSE' },
  { symbol: 'RELIANCE', exchange: 'NSE' },
  { symbol: 'TCS', exchange: 'NSE' },
  { symbol: 'HDFCBANK', exchange: 'NSE' },
  { symbol: 'INFY', exchange: 'NSE' },
  { symbol: 'ICICIBANK', exchange: 'NSE' },
  { symbol: 'SBIN', exchange: 'NSE' },
];

const initialState: MarketState = {
  overview: null,
  quotes: {},
  candles: {},
  watchlist: DEFAULT_WATCHLIST,
  selectedSymbol: 'NIFTY50',
  marketStatus: null,
  loading: false,
  error: null,
};

export const fetchMarketOverview = createAsyncThunk('market/fetchOverview', async () => {
  return await marketAPI.getOverview();
});

export const fetchQuote = createAsyncThunk(
  'market/fetchQuote',
  async ({ symbol, exchange }: { symbol: string; exchange: string }) => {
    const quote = await marketAPI.getQuote(symbol, exchange);
    return quote;
  }
);

export const fetchCandles = createAsyncThunk(
  'market/fetchCandles',
  async ({ symbol, exchange, interval, days }: { symbol: string; exchange: string; interval: string; days: number }) => {
    const candles = await marketAPI.getCandles(symbol, exchange, interval, days);
    return { symbol, candles };
  }
);

export const fetchMarketStatus = createAsyncThunk('market/fetchStatus', async () => {
  return await marketAPI.getStatus();
});

const marketSlice = createSlice({
  name: 'market',
  initialState,
  reducers: {
    updateQuote(state, action: PayloadAction<QuoteData>) {
      state.quotes[action.payload.symbol] = action.payload;
      // Also update watchlist item
      const idx = state.watchlist.findIndex((w) => w.symbol === action.payload.symbol);
      if (idx !== -1) {
        state.watchlist[idx].quote = action.payload;
      }
    },
    updatePriceFromWS(state, action: PayloadAction<Partial<QuoteData>[]>) {
      action.payload.forEach((update) => {
        if (!update.symbol) return;
        const existing = state.quotes[update.symbol];
        if (existing) {
          state.quotes[update.symbol] = { ...existing, ...update };
        } else {
          state.quotes[update.symbol] = update as QuoteData;
        }
        const idx = state.watchlist.findIndex((w) => w.symbol === update.symbol);
        if (idx !== -1) {
          state.watchlist[idx].quote = state.quotes[update.symbol];
        }
      });
    },
    setSelectedSymbol(state, action: PayloadAction<string>) {
      state.selectedSymbol = action.payload;
    },
    addToWatchlist(state, action: PayloadAction<WatchlistItem>) {
      const exists = state.watchlist.find((w) => w.symbol === action.payload.symbol);
      if (!exists) {
        state.watchlist.push(action.payload);
      }
    },
    removeFromWatchlist(state, action: PayloadAction<string>) {
      state.watchlist = state.watchlist.filter((w) => w.symbol !== action.payload);
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchMarketOverview.pending, (state) => { state.loading = true; })
      .addCase(fetchMarketOverview.fulfilled, (state, action) => {
        state.loading = false;
        state.overview = action.payload;
        // Cache quotes
        if (action.payload.nifty50) state.quotes['NIFTY50'] = action.payload.nifty50;
        if (action.payload.bank_nifty) state.quotes['BANKNIFTY'] = action.payload.bank_nifty;
        if (action.payload.sensex) state.quotes['SENSEX'] = action.payload.sensex;
      })
      .addCase(fetchMarketOverview.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch overview';
      })
      .addCase(fetchQuote.fulfilled, (state, action) => {
        if (action.payload) {
          state.quotes[action.payload.symbol] = action.payload;
        }
      })
      .addCase(fetchCandles.fulfilled, (state, action) => {
        state.candles[action.payload.symbol] = action.payload.candles;
      })
      .addCase(fetchMarketStatus.fulfilled, (state, action) => {
        state.marketStatus = action.payload;
      });
  },
});

export const {
  updateQuote, updatePriceFromWS, setSelectedSymbol,
  addToWatchlist, removeFromWatchlist,
} = marketSlice.actions;

export default marketSlice.reducer;
