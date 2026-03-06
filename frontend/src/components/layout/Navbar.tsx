'use client';

import { useState, useEffect } from 'react';
import { RefreshCw, Wifi, WifiOff, User } from 'lucide-react';
import { useAppDispatch } from '@/store';
import { fetchMarketOverview } from '@/store/marketSlice';
import { syncPortfolio } from '@/store/portfolioSlice';
import { marketWS } from '@/services/websocket';
import toast from 'react-hot-toast';

export function Navbar() {
  const dispatch = useAppDispatch();
  const [syncing, setSyncing] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [currentTime, setCurrentTime] = useState('');
  const user = typeof window !== 'undefined'
    ? JSON.parse(localStorage.getItem('user') || '{}')
    : {};

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(now.toLocaleTimeString('en-IN', {
        timeZone: 'Asia/Kolkata',
        hour12: false,
      }));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Poll WS connection status
  useEffect(() => {
    const interval = setInterval(() => {
      setWsConnected(marketWS.isConnected);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await dispatch(syncPortfolio());
      await dispatch(fetchMarketOverview());
      toast.success('Portfolio synced');
    } catch {
      toast.error('Sync failed');
    } finally {
      setSyncing(false);
    }
  };

  return (
    <header className="h-12 bg-bg-secondary border-b border-border flex items-center px-4 gap-4 flex-shrink-0">
      <div className="flex-1" />

      {/* IST Time */}
      <div className="font-trading text-sm text-text-secondary">
        {currentTime} IST
      </div>

      {/* WS Status */}
      <div className={`flex items-center gap-1.5 text-xs ${wsConnected ? 'text-bull' : 'text-bear'}`}>
        {wsConnected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
        <span>{wsConnected ? 'LIVE' : 'OFFLINE'}</span>
      </div>

      {/* Sync button */}
      <button
        onClick={handleSync}
        disabled={syncing}
        className="btn-ghost text-xs flex items-center gap-1.5 py-1.5 px-3"
      >
        <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
        Sync
      </button>

      {/* User */}
      <div className="flex items-center gap-2 text-sm">
        <div className="w-7 h-7 bg-accent-blue/20 text-accent-blue rounded-full flex items-center justify-center">
          <User className="w-4 h-4" />
        </div>
        <span className="text-text-secondary text-xs">{user?.username || 'Trader'}</span>
      </div>
    </header>
  );
}
