import { useEffect, useRef, useCallback } from 'react';
import { marketWS } from '@/services/websocket';
import { useAppDispatch } from '@/store';
import { updatePriceFromWS } from '@/store/marketSlice';
import { addSignalAlert } from '@/store/signalSlice';
import { WSMessage } from '@/types';

export function useWebSocket() {
  const dispatch = useAppDispatch();
  const connectedRef = useRef(false);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token || connectedRef.current) return;

    connectedRef.current = true;
    marketWS.connect(token);

    const unsubscribePrice = marketWS.onPriceUpdate((updates) => {
      dispatch(updatePriceFromWS(updates));
    });

    const unsubscribeMsg = marketWS.onMessage((msg: WSMessage) => {
      if (msg.type === 'signal_alert' && msg.data) {
        dispatch(addSignalAlert(msg.data));
      }
    });

    return () => {
      unsubscribePrice();
      unsubscribeMsg();
    };
  }, [dispatch]);

  const subscribe = useCallback((symbols: string[]) => {
    marketWS.subscribe(symbols);
  }, []);

  const unsubscribe = useCallback((symbols: string[]) => {
    marketWS.unsubscribe(symbols);
  }, []);

  return { subscribe, unsubscribe, isConnected: marketWS.isConnected };
}
