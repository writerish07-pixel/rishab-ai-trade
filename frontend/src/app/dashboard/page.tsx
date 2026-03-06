'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Sidebar } from '@/components/layout/Sidebar';
import { Navbar } from '@/components/layout/Navbar';
import { MarketOverviewBar } from '@/components/market/MarketOverviewBar';
import { Watchlist } from '@/components/market/Watchlist';
import { TradingChart } from '@/components/charts/TradingChart';
import { BuySellPanel } from '@/components/trading/BuySellPanel';
import { SignalPanel } from '@/components/trading/SignalPanel';
import { OrderBook } from '@/components/trading/OrderBook';
import { useMarketData } from '@/hooks/useMarketData';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAppDispatch } from '@/store';
import { fetchSignalSummary, scanMarket } from '@/store/signalSlice';

export default function DashboardPage() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const { selectedSymbol, selectSymbol, marketStatus } = useMarketData();
  useWebSocket(); // Initialize WS connection

  const [activeTab, setActiveTab] = useState<'chart' | 'signals' | 'orders'>('chart');

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.replace('/login');
      return;
    }
    // Load initial signals and scan
    dispatch(fetchSignalSummary());
    dispatch(scanMarket({ limit: 10 }));
  }, [router, dispatch]);

  return (
    <div className="flex h-screen bg-bg-primary overflow-hidden">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar />
        <MarketOverviewBar />

        <div className="flex-1 flex overflow-hidden">
          {/* Left: Watchlist */}
          <div className="w-60 border-r border-border flex-shrink-0 overflow-y-auto">
            <Watchlist onSelect={selectSymbol} selectedSymbol={selectedSymbol} />
          </div>

          {/* Center: Chart + controls */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Tab bar */}
            <div className="flex border-b border-border px-4 bg-bg-secondary">
              {([
                { key: 'chart', label: 'Chart & Analysis' },
                { key: 'signals', label: 'AI Signals' },
                { key: 'orders', label: 'Order Book' },
              ] as const).map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === tab.key
                      ? 'border-accent-blue text-accent-blue'
                      : 'border-transparent text-text-secondary hover:text-text-primary'
                  }`}
                >
                  {tab.label}
                </button>
              ))}

              {/* Market status pill */}
              <div className="ml-auto flex items-center pr-2">
                <span className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1 rounded-full ${
                  marketStatus?.is_open
                    ? 'bg-green-900/40 text-bull'
                    : 'bg-red-900/40 text-bear'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    marketStatus?.is_open ? 'bg-bull animate-pulse' : 'bg-bear'
                  }`} />
                  {marketStatus?.status || 'Loading...'}
                </span>
              </div>
            </div>

            {/* Tab content */}
            <div className="flex-1 overflow-auto p-4">
              {activeTab === 'chart' && <TradingChart symbol={selectedSymbol} />}
              {activeTab === 'signals' && <SignalPanel />}
              {activeTab === 'orders' && <OrderBook />}
            </div>
          </div>

          {/* Right: Buy/Sell Panel */}
          <div className="w-72 border-l border-border flex-shrink-0 overflow-y-auto">
            <BuySellPanel symbol={selectedSymbol} />
          </div>
        </div>
      </div>
    </div>
  );
}
