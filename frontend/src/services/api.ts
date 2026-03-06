import axios, { AxiosInstance, AxiosError } from 'axios';
import toast from 'react-hot-toast';
import {
  QuoteData, OHLCData, Signal, PlaceOrderRequest,
  Trade, Holding, Position, PortfolioOverview,
  MarketOverview, User
} from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_PREFIX = `${API_URL}/api/v1`;

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_PREFIX,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: attach token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle errors globally
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail: string }>) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    } else if (error.response?.status === 400) {
      const detail = error.response.data?.detail;
      if (detail) toast.error(detail);
    } else if (error.response?.status === 500) {
      toast.error('Server error. Please try again.');
    }
    return Promise.reject(error);
  }
);

// ============================================
// Auth
// ============================================
export const authAPI = {
  register: async (email: string, username: string, password: string) => {
    const { data } = await api.post('/auth/register', { email, username, password });
    return data as User;
  },

  login: async (email: string, password: string) => {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);
    const { data } = await api.post('/auth/token', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('user', JSON.stringify(data.user));
    return data as { access_token: string; token_type: string; user: User };
  },

  getMe: async () => {
    const { data } = await api.get('/auth/me');
    return data as User;
  },

  connectAngelOne: async (credentials: {
    api_key: string; client_id: string; password: string; totp_secret: string;
  }) => {
    const { data } = await api.post('/auth/angel-one/connect', null, { params: credentials });
    return data;
  },

  getAngelOneStatus: async () => {
    const { data } = await api.get('/auth/angel-one/status');
    return data as { is_connected: boolean; client_id?: string };
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.href = '/login';
  },
};

// ============================================
// Market Data
// ============================================
export const marketAPI = {
  getStatus: async () => {
    const { data } = await api.get('/market/status');
    return data;
  },

  getQuote: async (symbol: string, exchange = 'NSE') => {
    const { data } = await api.get(`/market/quote/${symbol}`, { params: { exchange } });
    return data as QuoteData;
  },

  getBulkQuotes: async (symbols: string[], exchange = 'NSE') => {
    const { data } = await api.get('/market/quotes', {
      params: { symbols: symbols.join(','), exchange },
    });
    return data as QuoteData[];
  },

  getCandles: async (symbol: string, exchange = 'NSE', interval = '5m', days = 3) => {
    const { data } = await api.get(`/market/candles/${symbol}`, {
      params: { exchange, interval, days },
    });
    return data as OHLCData[];
  },

  getOverview: async () => {
    const { data } = await api.get('/market/overview');
    return data as MarketOverview;
  },

  searchSymbol: async (query: string, exchange = 'NSE') => {
    const { data } = await api.get(`/market/search/${query}`, { params: { exchange } });
    return data.results as Array<{ symboltoken: string; tradingsymbol: string; name: string }>;
  },

  getOptionChain: async (symbol: string, expiry_date: string, strike_price: number) => {
    const { data } = await api.get(`/market/option-chain/${symbol}`, {
      params: { expiry_date, strike_price },
    });
    return data;
  },
};

// ============================================
// Orders
// ============================================
export const ordersAPI = {
  placeOrder: async (order: PlaceOrderRequest) => {
    const { data } = await api.post('/orders/place', order);
    return data;
  },

  cancelOrder: async (order_id: string) => {
    const { data } = await api.post('/orders/cancel', { order_id });
    return data;
  },

  getOrderBook: async () => {
    const { data } = await api.get('/orders/book');
    return data as any[];
  },

  getHistory: async (limit = 50) => {
    const { data } = await api.get('/orders/history', { params: { limit } });
    return data as Trade[];
  },

  getMargin: async () => {
    const { data } = await api.get('/orders/margin');
    return data;
  },
};

// ============================================
// Portfolio
// ============================================
export const portfolioAPI = {
  sync: async () => {
    const { data } = await api.get('/portfolio/sync');
    return data;
  },

  getOverview: async () => {
    const { data } = await api.get('/portfolio/overview');
    return data as PortfolioOverview;
  },

  getHoldings: async () => {
    const { data } = await api.get('/portfolio/holdings');
    return data as Holding[];
  },

  getPositions: async () => {
    const { data } = await api.get('/portfolio/positions');
    return data as Position[];
  },
};

// ============================================
// AI Signals
// ============================================
export const signalsAPI = {
  analyze: async (symbol: string, exchange = 'NSE', interval = '5m', days = 3) => {
    const { data } = await api.get(`/signals/analyze/${symbol}`, {
      params: { exchange, interval, days },
    });
    return data as Signal & { id?: number };
  },

  scanMarket: async (limit = 10, exchange = 'NSE') => {
    const { data } = await api.get('/signals/scan/market', { params: { limit, exchange } });
    return data as { signals: Signal[]; total_scanned: number; total_signals: number };
  },

  getSummary: async () => {
    const { data } = await api.get('/signals/summary');
    return data;
  },

  getHistory: async (limit = 20) => {
    const { data } = await api.get('/signals/history', { params: { limit } });
    return data as Signal[];
  },

  getInstitutional: async (symbols: string[]) => {
    const { data } = await api.get('/signals/institutional', {
      params: { symbols: symbols.join(',') },
    });
    return data.data;
  },
};

export default api;
