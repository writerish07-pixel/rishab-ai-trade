import { WSMessage, QuoteData } from '@/types';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

type MessageHandler = (msg: WSMessage) => void;
type PriceUpdateHandler = (updates: Partial<QuoteData>[]) => void;

class MarketWebSocket {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnects = 10;
  private reconnectDelay = 2000;
  private messageHandlers: MessageHandler[] = [];
  private priceHandlers: PriceUpdateHandler[] = [];
  private subscribedSymbols: Set<string> = new Set();
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private isIntentionalClose = false;

  connect(token: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this.isIntentionalClose = false;

    const url = `${WS_URL}/ws/market?token=${encodeURIComponent(token)}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log('[WS] Connected');
      this.reconnectAttempts = 0;
      this.reconnectDelay = 2000;
      this._startPing();

      // Re-subscribe to previous symbols
      if (this.subscribedSymbols.size > 0) {
        this.subscribe(Array.from(this.subscribedSymbols));
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
        this.messageHandlers.forEach((h) => h(msg));

        if (msg.type === 'price_update' && msg.data) {
          this.priceHandlers.forEach((h) => h(msg.data));
        }
      } catch (e) {
        console.error('[WS] Parse error:', e);
      }
    };

    this.ws.onclose = () => {
      this._stopPing();
      if (!this.isIntentionalClose && this.reconnectAttempts < this.maxReconnects) {
        console.log(`[WS] Reconnecting in ${this.reconnectDelay}ms...`);
        setTimeout(() => {
          this.reconnectAttempts++;
          this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 30000);
          this.connect(token);
        }, this.reconnectDelay);
      }
    };

    this.ws.onerror = (error) => {
      console.error('[WS] Error:', error);
    };
  }

  subscribe(symbols: string[]): void {
    symbols.forEach((s) => this.subscribedSymbols.add(s.toUpperCase()));
    this._send({ action: 'subscribe', symbols });
  }

  unsubscribe(symbols: string[]): void {
    symbols.forEach((s) => this.subscribedSymbols.delete(s.toUpperCase()));
    this._send({ action: 'unsubscribe', symbols });
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.push(handler);
    return () => {
      this.messageHandlers = this.messageHandlers.filter((h) => h !== handler);
    };
  }

  onPriceUpdate(handler: PriceUpdateHandler): () => void {
    this.priceHandlers.push(handler);
    return () => {
      this.priceHandlers = this.priceHandlers.filter((h) => h !== handler);
    };
  }

  disconnect(): void {
    this.isIntentionalClose = true;
    this._stopPing();
    this.ws?.close();
    this.ws = null;
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private _send(data: object): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  private _startPing(): void {
    this.pingInterval = setInterval(() => {
      this._send({ action: 'ping' });
    }, 25000);
  }

  private _stopPing(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }
}

// Singleton instance
export const marketWS = new MarketWebSocket();
export default marketWS;
