import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { Holding, Position, PortfolioOverview, Trade } from '@/types';
import { portfolioAPI, ordersAPI } from '@/services/api';

interface PortfolioState {
  overview: PortfolioOverview | null;
  holdings: Holding[];
  positions: Position[];
  orderHistory: Trade[];
  orderBook: any[];
  loading: boolean;
  syncing: boolean;
  error: string | null;
}

const initialState: PortfolioState = {
  overview: null,
  holdings: [],
  positions: [],
  orderHistory: [],
  orderBook: [],
  loading: false,
  syncing: false,
  error: null,
};

export const syncPortfolio = createAsyncThunk('portfolio/sync', async () => {
  return await portfolioAPI.sync();
});

export const fetchPortfolioOverview = createAsyncThunk('portfolio/fetchOverview', async () => {
  return await portfolioAPI.getOverview();
});

export const fetchHoldings = createAsyncThunk('portfolio/fetchHoldings', async () => {
  return await portfolioAPI.getHoldings();
});

export const fetchPositions = createAsyncThunk('portfolio/fetchPositions', async () => {
  return await portfolioAPI.getPositions();
});

export const fetchOrderHistory = createAsyncThunk('portfolio/fetchHistory', async () => {
  return await ordersAPI.getHistory(100);
});

export const fetchOrderBook = createAsyncThunk('portfolio/fetchOrderBook', async () => {
  return await ordersAPI.getOrderBook();
});

const portfolioSlice = createSlice({
  name: 'portfolio',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(syncPortfolio.pending, (state) => { state.syncing = true; })
      .addCase(syncPortfolio.fulfilled, (state) => { state.syncing = false; })
      .addCase(syncPortfolio.rejected, (state) => { state.syncing = false; })
      .addCase(fetchPortfolioOverview.fulfilled, (state, action) => {
        state.overview = action.payload;
      })
      .addCase(fetchHoldings.pending, (state) => { state.loading = true; })
      .addCase(fetchHoldings.fulfilled, (state, action) => {
        state.loading = false;
        state.holdings = action.payload;
      })
      .addCase(fetchPositions.fulfilled, (state, action) => {
        state.positions = action.payload;
      })
      .addCase(fetchOrderHistory.fulfilled, (state, action) => {
        state.orderHistory = action.payload;
      })
      .addCase(fetchOrderBook.fulfilled, (state, action) => {
        state.orderBook = action.payload;
      });
  },
});

export default portfolioSlice.reducer;
