'use client';

import { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/store';
import {
  fetchHoldings, fetchPositions, fetchPortfolioOverview, syncPortfolio
} from '@/store/portfolioSlice';
import { Sidebar } from '@/components/layout/Sidebar';
import { Navbar } from '@/components/layout/Navbar';
import { RefreshCw, TrendingUp, TrendingDown } from 'lucide-react';
import toast from 'react-hot-toast';

export default function PortfolioPage() {
  const dispatch = useAppDispatch();
  const { overview, holdings, positions, syncing } = useAppSelector((s) => s.portfolio);

  useEffect(() => {
    dispatch(fetchPortfolioOverview());
    dispatch(fetchHoldings());
    dispatch(fetchPositions());
  }, [dispatch]);

  const handleSync = async () => {
    try {
      await dispatch(syncPortfolio()).unwrap();
      dispatch(fetchPortfolioOverview());
      dispatch(fetchHoldings());
      dispatch(fetchPositions());
      toast.success('Portfolio synced from Angel One');
    } catch {
      toast.error('Sync failed. Check Angel One connection.');
    }
  };

  const totalPnlColor = (overview?.total_pnl ?? 0) >= 0 ? 'text-bull' : 'text-bear';
  const todayPnlColor = (overview?.today_pnl ?? 0) >= 0 ? 'text-bull' : 'text-bear';

  return (
    <div className="flex h-screen bg-bg-primary overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar />
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold text-text-primary">Portfolio</h1>
            <button
              onClick={handleSync}
              disabled={syncing}
              className="btn-primary flex items-center gap-2 text-sm"
            >
              <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
              Sync from Angel One
            </button>
          </div>

          {/* Overview cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'Portfolio Value', value: overview?.current_value ?? 0, colored: false },
              { label: 'Total Investment', value: overview?.total_investment ?? 0, colored: false },
              { label: 'Today P&L', value: overview?.today_pnl ?? 0, colored: true },
              { label: 'Total P&L', value: overview?.total_pnl ?? 0, colored: true },
              { label: 'Unrealized P&L', value: overview?.unrealized_pnl ?? 0, colored: true },
              { label: 'Realized P&L', value: overview?.realized_pnl ?? 0, colored: true },
              { label: 'Available Margin', value: overview?.available_margin ?? 0, colored: false },
              { label: 'Used Margin', value: overview?.used_margin ?? 0, colored: false },
            ].map(({ label, value, colored }) => (
              <div key={label} className="card">
                <div className="text-xs text-text-muted mb-1.5">{label}</div>
                <div className={`font-trading text-xl font-bold ${
                  colored
                    ? value >= 0 ? 'text-bull' : 'text-bear'
                    : 'text-text-primary'
                }`}>
                  ₹{Math.abs(value).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                </div>
                {colored && (
                  <div className={`flex items-center gap-1 text-xs mt-0.5 ${value >= 0 ? 'text-bull' : 'text-bear'}`}>
                    {value >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                    {value >= 0 ? 'Profit' : 'Loss'}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Open Positions */}
          <div>
            <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-3">
              Open Positions ({positions.length})
            </h2>
            {positions.length === 0 ? (
              <div className="card py-10 text-center text-text-muted text-sm">
                No open intraday positions
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-border">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-bg-secondary text-xs">
                      {['Symbol', 'Product', 'Qty', 'Avg Buy', 'Avg Sell', 'LTP', 'P&L', 'Unrealized P&L'].map((h) => (
                        <th key={h} className="text-left px-4 py-3 text-text-muted font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map((pos) => (
                      <tr key={pos.id} className="border-b border-border/50 hover:bg-bg-hover transition-colors">
                        <td className="px-4 py-3 font-medium text-text-primary">{pos.symbol}</td>
                        <td className="px-4 py-3 text-text-secondary text-xs">{pos.product_type}</td>
                        <td className="px-4 py-3 font-trading">{pos.quantity}</td>
                        <td className="px-4 py-3 font-trading">₹{pos.avg_buy_price.toFixed(2)}</td>
                        <td className="px-4 py-3 font-trading">₹{pos.avg_sell_price.toFixed(2)}</td>
                        <td className="px-4 py-3 font-trading">₹{pos.current_price.toFixed(2)}</td>
                        <td className={`px-4 py-3 font-trading font-bold ${pos.pnl >= 0 ? 'text-bull' : 'text-bear'}`}>
                          {pos.pnl >= 0 ? '+' : ''}₹{pos.pnl.toFixed(2)}
                        </td>
                        <td className={`px-4 py-3 font-trading font-bold ${pos.unrealized_pnl >= 0 ? 'text-bull' : 'text-bear'}`}>
                          {pos.unrealized_pnl >= 0 ? '+' : ''}₹{pos.unrealized_pnl.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Holdings */}
          <div>
            <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-3">
              Holdings ({holdings.length})
            </h2>
            {holdings.length === 0 ? (
              <div className="card py-10 text-center text-text-muted text-sm">
                No holdings found. Sync your Angel One account to see holdings.
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-border">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-bg-secondary text-xs">
                      {['Symbol', 'Qty', 'Avg Price', 'LTP', 'Current Value', 'P&L', 'P&L %'].map((h) => (
                        <th key={h} className="text-left px-4 py-3 text-text-muted font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {holdings.map((h) => (
                      <tr key={h.id} className="border-b border-border/50 hover:bg-bg-hover transition-colors">
                        <td className="px-4 py-3 font-medium text-text-primary">{h.symbol}</td>
                        <td className="px-4 py-3 font-trading">{h.quantity}</td>
                        <td className="px-4 py-3 font-trading">₹{h.avg_buy_price.toFixed(2)}</td>
                        <td className="px-4 py-3 font-trading">₹{h.current_price.toFixed(2)}</td>
                        <td className="px-4 py-3 font-trading">₹{h.current_value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
                        <td className={`px-4 py-3 font-trading font-bold ${h.pnl >= 0 ? 'text-bull' : 'text-bear'}`}>
                          {h.pnl >= 0 ? '+' : ''}₹{h.pnl.toFixed(2)}
                        </td>
                        <td className={`px-4 py-3 font-trading font-bold ${h.pnl_percent >= 0 ? 'text-bull' : 'text-bear'}`}>
                          {h.pnl_percent >= 0 ? '+' : ''}{h.pnl_percent.toFixed(2)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
