'use client';

import { useEffect, useRef, useState } from 'react';
import {
  createChart, IChartApi, ISeriesApi, CandlestickData,
  ColorType, CrosshairMode
} from 'lightweight-charts';
import { useAppDispatch, useAppSelector } from '@/store';
import { fetchCandles, setSelectedSymbol } from '@/store/marketSlice';
import { analyzeSymbol } from '@/store/signalSlice';
import { OHLCData } from '@/types';
import { BarChart2, TrendingUp, Loader2, Zap } from 'lucide-react';
import toast from 'react-hot-toast';
import { SignalOverlay } from './SignalOverlay';

const INTERVALS = ['1m', '5m', '15m', '30m', '1h', '1d'] as const;
type Interval = typeof INTERVALS[number];

interface Props {
  symbol: string;
}

export function TradingChart({ symbol }: Props) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeRef = useRef<ISeriesApi<'Histogram'> | null>(null);

  const dispatch = useAppDispatch();
  const candles = useAppSelector((state) => state.market.candles[symbol] || []);
  const currentSignal = useAppSelector((state) => state.signals.currentAnalysis);
  const { loading: signalLoading } = useAppSelector((state) => state.signals);

  const [interval, setInterval] = useState<Interval>('5m');
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Load candles when symbol/interval changes
  useEffect(() => {
    dispatch(fetchCandles({ symbol, exchange: 'NSE', interval, days: interval === '1d' ? 365 : 5 }));
  }, [symbol, interval, dispatch]);

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#1a2235' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: '#1e293b' },
        horzLines: { color: '#1e293b' },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: '#1e293b' },
      timeScale: {
        borderColor: '#1e293b',
        timeVisible: true,
        secondsVisible: false,
      },
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight,
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderUpColor: '#22c55e',
      borderDownColor: '#ef4444',
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    });

    const volumeSeries = chart.addHistogramSeries({
      color: '#26a69a',
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    chartRef.current = chart;
    candlestickRef.current = candleSeries;
    volumeRef.current = volumeSeries;

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, []);

  // Update chart data when candles change
  useEffect(() => {
    if (!candlestickRef.current || !volumeRef.current || !candles.length) return;

    const candleData: CandlestickData[] = candles.map((c: OHLCData) => ({
      time: (new Date(c.timestamp).getTime() / 1000) as any,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));

    const volumeData = candles.map((c: OHLCData) => ({
      time: (new Date(c.timestamp).getTime() / 1000) as any,
      value: c.volume,
      color: c.close >= c.open ? 'rgba(34,197,94,0.4)' : 'rgba(239,68,68,0.4)',
    }));

    candlestickRef.current.setData(candleData);
    volumeRef.current.setData(volumeData);
    chartRef.current?.timeScale().fitContent();
  }, [candles]);

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    try {
      await dispatch(analyzeSymbol({ symbol, exchange: 'NSE', interval, days: 5 })).unwrap();
      toast.success(`AI analysis complete for ${symbol}`);
    } catch {
      toast.error('Analysis failed');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const lastCandle = candles[candles.length - 1];
  const prevCandle = candles[candles.length - 2];
  const change = lastCandle && prevCandle ? lastCandle.close - prevCandle.close : 0;
  const changePct = prevCandle ? (change / prevCandle.close) * 100 : 0;

  return (
    <div className="flex flex-col h-full gap-3">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-4">
          <div>
            <h2 className="text-lg font-bold text-text-primary">{symbol}</h2>
            {lastCandle && (
              <div className="flex items-center gap-2">
                <span className="font-trading text-2xl font-bold text-text-primary">
                  {lastCandle.close.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                </span>
                <span className={`font-trading text-sm font-medium ${change >= 0 ? 'text-bull' : 'text-bear'}`}>
                  {change >= 0 ? '+' : ''}{change.toFixed(2)} ({changePct.toFixed(2)}%)
                </span>
              </div>
            )}
          </div>
          {lastCandle && (
            <div className="hidden lg:flex items-center gap-4 text-xs text-text-muted font-trading">
              <span>O: <span className="text-text-secondary">{lastCandle.open.toFixed(2)}</span></span>
              <span>H: <span className="text-bull">{lastCandle.high.toFixed(2)}</span></span>
              <span>L: <span className="text-bear">{lastCandle.low.toFixed(2)}</span></span>
              <span>V: <span className="text-text-secondary">{(lastCandle.volume / 1000).toFixed(0)}K</span></span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Interval selector */}
          <div className="flex bg-bg-secondary rounded-lg p-0.5 border border-border">
            {INTERVALS.map((i) => (
              <button
                key={i}
                onClick={() => setInterval(i)}
                className={`px-2.5 py-1 text-xs rounded-md transition-all ${
                  interval === i
                    ? 'bg-accent-blue text-white'
                    : 'text-text-muted hover:text-text-primary'
                }`}
              >
                {i}
              </button>
            ))}
          </div>

          {/* AI Analyze button */}
          <button
            onClick={handleAnalyze}
            disabled={isAnalyzing || signalLoading}
            className="btn-primary text-xs flex items-center gap-1.5 py-2"
          >
            {isAnalyzing ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Zap className="w-3.5 h-3.5" />
            )}
            AI Analyze
          </button>
        </div>
      </div>

      {/* Signal overlay (entry/sl/target lines) */}
      {currentSignal && currentSignal.symbol === symbol && (
        <SignalOverlay signal={currentSignal} />
      )}

      {/* Chart */}
      <div className="flex-1 rounded-xl overflow-hidden border border-border">
        <div ref={chartContainerRef} className="w-full h-full" />
      </div>
    </div>
  );
}
