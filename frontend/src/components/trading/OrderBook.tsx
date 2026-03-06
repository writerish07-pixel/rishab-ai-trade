'use client';

import { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/store';
import { fetchOrderBook, fetchOrderHistory, fetchPortfolioOverview, syncPortfolio } from '@/store/portfolioSlice';
import { ordersAPI } from '@/services/api';
import { RefreshCw, CheckCircle, XCircle, Clock, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { format } from 'date-fns';

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    complete: 'badge-bull',
    COMPLETE: 'badge-bull',
    open: 'badge-blue',
    OPEN: 'badge-blue',
    cancelled: 'bg-gray-700/40 text-gray-400',
    CANCELLED: 'bg-gray-700/40 text-gray-400',
    rejected: 'badge-bear',
    REJECTED: 'badge-bear',
    pending: 'badge-neutral',
    PENDING: 'badge-neutral',
  };
  return <span className={`badge ${map[status] || 'badge-neutral'}`}>{status}</span>;
}

export function OrderBook() {
  const dispatch = useAppDispatch();
  const { orderBook, orderHistory, overview, syncing } = useAppSelector((state) => state.portfolio);

  useEffect(() => {
    dispatch(fetchOrderBook());
    dispatch(fetchOrderHistory());
    dispatch(fetchPortfolioOverview());
  }, [dispatch]);

  const handleCancel = async (orderId: string) => {
    try {
      await ordersAPI.cancelOrder(orderId);
      toast.success('Order cancelled');
      dispatch(fetchOrderBook());
    } catch {
      toast.error('Failed to cancel order');
    }
  };

  const handleSync = () => {
    dispatch(syncPortfolio());
    setTimeout(() => {
      dispatch(fetchOrderBook());
      dispatch(fetchPortfolioOverview());
    }, 2000);
  };

  return (
    <div className="space-y-6">
      {/* P&L Summary */}
      {overview && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: 'Today P&L', value: overview.today_pnl, colored: true },
            { label: 'Unrealized P&L', value: overview.unrealized_pnl, colored: true },
            { label: 'Available Margin', value: overview.available_margin, colored: false },
            { label: 'Portfolio Value', value: overview.current_value, colored: false },
          ].map(({ label, value, colored }) => (
            <div key={label} className="card">
              <div className="text-xs text-text-muted mb-1">{label}</div>
              <div className={`font-trading font-bold text-lg ${
                colored
                  ? value >= 0 ? 'text-bull' : 'text-bear'
                  : 'text-text-primary'
              }`}>
                ₹{Math.abs(value).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                {colored && value < 0 && ' (Loss)'}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Live Order Book */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-text-primary">Live Order Book</h3>
          <button
            onClick={handleSync}
            disabled={syncing}
            className="btn-ghost text-xs flex items-center gap-1.5 py-1.5 px-3"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
            Sync
          </button>
        </div>

        {orderBook.length === 0 ? (
          <div className="card flex items-center justify-center py-10 text-text-muted text-sm">
            No orders placed today
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-border">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border bg-bg-secondary">
                  {['Symbol', 'Type', 'Side', 'Qty', 'Price', 'Status', 'Time', 'Action'].map((h) => (
                    <th key={h} className="text-left px-3 py-2.5 text-text-muted font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {orderBook.map((order: any, i: number) => (
                  <tr key={i} className="border-b border-border/50 hover:bg-bg-hover transition-colors">
                    <td className="px-3 py-2.5 font-medium text-text-primary">{order.tradingsymbol || order.symbol}</td>
                    <td className="px-3 py-2.5 text-text-secondary">{order.ordertype}</td>
                    <td className="px-3 py-2.5">
                      <span className={order.transactiontype === 'BUY' ? 'text-bull font-medium' : 'text-bear font-medium'}>
                        {order.transactiontype}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 font-trading text-text-primary">{order.quantity}</td>
                    <td className="px-3 py-2.5 font-trading text-text-primary">
                      ₹{parseFloat(order.price || 0).toFixed(2)}
                    </td>
                    <td className="px-3 py-2.5"><StatusBadge status={order.status} /></td>
                    <td className="px-3 py-2.5 text-text-muted">{order.updatetime || '—'}</td>
                    <td className="px-3 py-2.5">
                      {['open', 'OPEN', 'pending', 'PENDING'].includes(order.status) && (
                        <button
                          onClick={() => handleCancel(order.orderid)}
                          className="text-bear hover:text-red-400 transition-colors"
                          title="Cancel order"
                        >
                          <XCircle className="w-4 h-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Trade History */}
      <div>
        <h3 className="text-sm font-semibold text-text-primary mb-3">Trade History</h3>
        {orderHistory.length === 0 ? (
          <div className="card flex items-center justify-center py-10 text-text-muted text-sm">
            No trade history found
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-border">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border bg-bg-secondary">
                  {['Symbol', 'Side', 'Qty', 'Price', 'P&L', 'Status', 'AI Order', 'Date'].map((h) => (
                    <th key={h} className="text-left px-3 py-2.5 text-text-muted font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {orderHistory.map((trade) => (
                  <tr key={trade.id} className="border-b border-border/50 hover:bg-bg-hover transition-colors">
                    <td className="px-3 py-2.5 font-medium text-text-primary">{trade.symbol}</td>
                    <td className={`px-3 py-2.5 font-medium ${trade.order_side === 'BUY' ? 'text-bull' : 'text-bear'}`}>
                      {trade.order_side}
                    </td>
                    <td className="px-3 py-2.5 font-trading text-text-primary">{trade.quantity}</td>
                    <td className="px-3 py-2.5 font-trading text-text-primary">₹{trade.executed_price.toFixed(2)}</td>
                    <td className={`px-3 py-2.5 font-trading font-bold ${trade.pnl >= 0 ? 'text-bull' : 'text-bear'}`}>
                      {trade.pnl >= 0 ? '+' : ''}₹{trade.pnl.toFixed(2)}
                    </td>
                    <td className="px-3 py-2.5"><StatusBadge status={trade.status} /></td>
                    <td className="px-3 py-2.5">
                      {trade.is_algo_order
                        ? <span className="badge badge-blue">AI</span>
                        : <span className="text-text-muted">Manual</span>
                      }
                    </td>
                    <td className="px-3 py-2.5 text-text-muted">
                      {format(new Date(trade.created_at), 'dd MMM HH:mm')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
