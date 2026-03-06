'use client';

import { Provider } from 'react-redux';
import { Toaster } from 'react-hot-toast';
import { store } from '@/store';

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <Provider store={store}>
      {children}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#1a2235',
            color: '#f1f5f9',
            border: '1px solid #1e293b',
            borderRadius: '8px',
          },
          success: { iconTheme: { primary: '#22c55e', secondary: '#1a2235' } },
          error: { iconTheme: { primary: '#ef4444', secondary: '#1a2235' } },
        }}
      />
    </Provider>
  );
}
