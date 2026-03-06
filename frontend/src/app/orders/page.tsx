'use client';

import { useEffect } from 'react';
import { useAppDispatch } from '@/store';
import { fetchOrderBook, fetchOrderHistory, fetchPortfolioOverview } from '@/store/portfolioSlice';
import { Sidebar } from '@/components/layout/Sidebar';
import { Navbar } from '@/components/layout/Navbar';
import { OrderBook } from '@/components/trading/OrderBook';

export default function OrdersPage() {
  const dispatch = useAppDispatch();

  useEffect(() => {
    dispatch(fetchOrderBook());
    dispatch(fetchOrderHistory());
    dispatch(fetchPortfolioOverview());
  }, [dispatch]);

  return (
    <div className="flex h-screen bg-bg-primary overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar />
        <div className="flex-1 overflow-y-auto p-6">
          <h1 className="text-xl font-bold text-text-primary mb-6">Orders & Trade History</h1>
          <OrderBook />
        </div>
      </div>
    </div>
  );
}
