'use client';

import { useState, useEffect } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { Navbar } from '@/components/layout/Navbar';
import { authAPI } from '@/services/api';
import { Link2, CheckCircle, XCircle, Eye, EyeOff, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';

export default function SettingsPage() {
  const [angelCreds, setAngelCreds] = useState({
    api_key: '', client_id: '', password: '', totp_secret: ''
  });
  const [angelStatus, setAngelStatus] = useState<{ is_connected: boolean; client_id?: string } | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [showSecrets, setShowSecrets] = useState(false);

  useEffect(() => {
    authAPI.getAngelOneStatus().then(setAngelStatus).catch(() => {});
  }, []);

  const handleConnectAngel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!angelCreds.api_key || !angelCreds.client_id || !angelCreds.password || !angelCreds.totp_secret) {
      toast.error('All Angel One fields are required');
      return;
    }
    setConnecting(true);
    try {
      await authAPI.connectAngelOne(angelCreds);
      toast.success('Angel One connected successfully!');
      const status = await authAPI.getAngelOneStatus();
      setAngelStatus(status);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Connection failed. Check credentials.');
    } finally {
      setConnecting(false);
    }
  };

  return (
    <div className="flex h-screen bg-bg-primary overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar />
        <div className="flex-1 overflow-y-auto p-6 max-w-2xl mx-auto w-full">
          <h1 className="text-xl font-bold text-text-primary mb-6">Settings</h1>

          {/* Angel One Connection */}
          <div className="card space-y-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-accent-blue/10 rounded-xl flex items-center justify-center">
                  <Link2 className="w-5 h-5 text-accent-blue" />
                </div>
                <div>
                  <h2 className="font-semibold text-text-primary">Angel One SmartAPI</h2>
                  <p className="text-xs text-text-muted">Real-time order execution & portfolio data</p>
                </div>
              </div>
              {angelStatus && (
                <div className={`flex items-center gap-1.5 text-sm font-medium ${
                  angelStatus.is_connected ? 'text-bull' : 'text-text-muted'
                }`}>
                  {angelStatus.is_connected
                    ? <><CheckCircle className="w-4 h-4" /> Connected ({angelStatus.client_id})</>
                    : <><XCircle className="w-4 h-4" /> Not Connected</>
                  }
                </div>
              )}
            </div>

            <div className="bg-bg-secondary rounded-lg p-4 border border-border text-xs text-text-muted space-y-1">
              <p>1. Visit <span className="text-accent-blue">smartapi.angelbroking.com</span> and create an API app</p>
              <p>2. Get your API Key, Client ID (your Angel One ID)</p>
              <p>3. Your trading password and TOTP secret (from authenticator setup)</p>
              <p>4. Enter below and click Connect</p>
            </div>

            <form onSubmit={handleConnectAngel} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-text-muted mb-1.5 block">API Key</label>
                  <input
                    type="text"
                    className="input text-sm"
                    placeholder="a1b2c3d4e5..."
                    value={angelCreds.api_key}
                    onChange={(e) => setAngelCreds((c) => ({ ...c, api_key: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-xs text-text-muted mb-1.5 block">Client ID</label>
                  <input
                    type="text"
                    className="input text-sm"
                    placeholder="A12345"
                    value={angelCreds.client_id}
                    onChange={(e) => setAngelCreds((c) => ({ ...c, client_id: e.target.value }))}
                  />
                </div>
              </div>
              <div>
                <label className="text-xs text-text-muted mb-1.5 block">Trading Password</label>
                <div className="relative">
                  <input
                    type={showSecrets ? 'text' : 'password'}
                    className="input text-sm pr-10"
                    placeholder="Your Angel One PIN"
                    value={angelCreds.password}
                    onChange={(e) => setAngelCreds((c) => ({ ...c, password: e.target.value }))}
                  />
                  <button
                    type="button"
                    onClick={() => setShowSecrets(!showSecrets)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
                  >
                    {showSecrets ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <div>
                <label className="text-xs text-text-muted mb-1.5 block">
                  TOTP Secret (Base32)
                  <span className="ml-2 text-text-muted normal-case font-normal">
                    — from Google Authenticator setup
                  </span>
                </label>
                <input
                  type={showSecrets ? 'text' : 'password'}
                  className="input text-sm font-trading"
                  placeholder="JBSWY3DPEHPK3PXP..."
                  value={angelCreds.totp_secret}
                  onChange={(e) => setAngelCreds((c) => ({ ...c, totp_secret: e.target.value.toUpperCase() }))}
                />
              </div>

              <button
                type="submit"
                disabled={connecting}
                className="btn-primary w-full flex items-center justify-center gap-2"
              >
                {connecting ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Connecting...</>
                ) : (
                  <><Link2 className="w-4 h-4" /> Connect Angel One</>
                )}
              </button>
            </form>
          </div>

          {/* Security Notice */}
          <div className="mt-4 p-4 bg-yellow-950/20 border border-yellow-500/20 rounded-xl">
            <p className="text-xs text-yellow-400 font-medium mb-1">Security Note</p>
            <p className="text-xs text-text-muted">
              Your Angel One credentials are stored encrypted in the database and used only to communicate with the Angel One SmartAPI.
              They are never shared with third parties. Use a dedicated API app — not your personal login — for added security.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
