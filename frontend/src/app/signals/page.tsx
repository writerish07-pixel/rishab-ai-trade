'use client';

import { useEffect } from 'react';
import { useAppDispatch } from '@/store';
import { scanMarket, fetchSignalSummary } from '@/store/signalSlice';
import { Sidebar } from '@/components/layout/Sidebar';
import { Navbar } from '@/components/layout/Navbar';
import { MarketOverviewBar } from '@/components/market/MarketOverviewBar';
import { SignalPanel } from '@/components/trading/SignalPanel';

export default function SignalsPage() {
  const dispatch = useAppDispatch();

  useEffect(() => {
    dispatch(fetchSignalSummary());
    dispatch(scanMarket({ limit: 20 }));
  }, [dispatch]);

  return (
    <div className="flex h-screen bg-bg-primary overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar />
        <MarketOverviewBar />
        <div className="flex-1 overflow-y-auto p-6">
          <div className="mb-4">
            <h1 className="text-xl font-bold text-text-primary">AI Signal Scanner</h1>
            <p className="text-text-muted text-sm mt-1">
              Real-time AI-powered intraday signals with entry, stop loss and targets
            </p>
          </div>
          <SignalPanel />
        </div>
      </div>
    </div>
  );
}
