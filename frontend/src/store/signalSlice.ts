import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Signal } from '@/types';
import { signalsAPI } from '@/services/api';

interface SignalState {
  activeSignals: Signal[];
  signalHistory: Signal[];
  currentAnalysis: Signal | null;
  marketSentiment: string;
  niftyTrend: string;
  bankNiftyTrend: string;
  loading: boolean;
  scanning: boolean;
  error: string | null;
}

const initialState: SignalState = {
  activeSignals: [],
  signalHistory: [],
  currentAnalysis: null,
  marketSentiment: 'NEUTRAL',
  niftyTrend: 'SIDEWAYS',
  bankNiftyTrend: 'SIDEWAYS',
  loading: false,
  scanning: false,
  error: null,
};

export const analyzeSymbol = createAsyncThunk(
  'signals/analyze',
  async ({ symbol, exchange, interval, days }: { symbol: string; exchange?: string; interval?: string; days?: number }) => {
    return await signalsAPI.analyze(symbol, exchange, interval, days);
  }
);

export const scanMarket = createAsyncThunk(
  'signals/scanMarket',
  async ({ limit, exchange }: { limit?: number; exchange?: string }) => {
    return await signalsAPI.scanMarket(limit, exchange);
  }
);

export const fetchSignalSummary = createAsyncThunk('signals/fetchSummary', async () => {
  return await signalsAPI.getSummary();
});

export const fetchSignalHistory = createAsyncThunk('signals/fetchHistory', async (limit: number = 20) => {
  return await signalsAPI.getHistory(limit);
});

const signalSlice = createSlice({
  name: 'signals',
  initialState,
  reducers: {
    addSignalAlert(state, action: PayloadAction<Signal>) {
      // Push real-time signal from WebSocket
      const exists = state.activeSignals.find((s) => s.symbol === action.payload.symbol);
      if (!exists) {
        state.activeSignals.unshift(action.payload);
        if (state.activeSignals.length > 20) {
          state.activeSignals.pop();
        }
      }
    },
    clearCurrentAnalysis(state) {
      state.currentAnalysis = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(analyzeSymbol.pending, (state) => { state.loading = true; state.error = null; })
      .addCase(analyzeSymbol.fulfilled, (state, action) => {
        state.loading = false;
        state.currentAnalysis = action.payload;
      })
      .addCase(analyzeSymbol.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Analysis failed';
      })
      .addCase(scanMarket.pending, (state) => { state.scanning = true; })
      .addCase(scanMarket.fulfilled, (state, action) => {
        state.scanning = false;
        state.activeSignals = action.payload.signals;
      })
      .addCase(scanMarket.rejected, (state) => { state.scanning = false; })
      .addCase(fetchSignalSummary.fulfilled, (state, action) => {
        state.marketSentiment = action.payload.market_sentiment;
        state.niftyTrend = action.payload.nifty_trend;
        state.bankNiftyTrend = action.payload.bank_nifty_trend;
        if (action.payload.top_signals) {
          state.activeSignals = action.payload.top_signals;
        }
      })
      .addCase(fetchSignalHistory.fulfilled, (state, action) => {
        state.signalHistory = action.payload;
      });
  },
});

export const { addSignalAlert, clearCurrentAnalysis } = signalSlice.actions;
export default signalSlice.reducer;
