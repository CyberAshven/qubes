/**
 * WalletConnect Context
 *
 * Provides wallet connection state to the entire app.
 * Wraps the walletConnect service with React state management.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import * as wc from '../services/walletConnect';

interface WalletState {
  connected: boolean;
  address: string | null;
  connecting: boolean;
  error: string | null;
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  signTransaction: (wcTransaction: string) => Promise<wc.WcSignResult>;
}

const WalletContext = createContext<WalletState>({
  connected: false,
  address: null,
  connecting: false,
  error: null,
  connect: async () => {},
  disconnect: async () => {},
  signTransaction: async () => ({ signedTransaction: '', signedTransactionHash: '' }),
});

export function WalletProvider({ children }: { children: React.ReactNode }) {
  const [connected, setConnected] = useState(false);
  const [address, setAddress] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Listen for session changes (including restored sessions)
  useEffect(() => {
    const unsub = wc.onSessionChange((session) => {
      if (session) {
        setConnected(true);
        setAddress(session.address);
      } else {
        setConnected(false);
        setAddress(null);
      }
    });

    // Check for existing session on mount
    const existing = wc.getSession();
    if (existing) {
      setConnected(true);
      setAddress(existing.address);
    }

    return unsub;
  }, []);

  const connect = useCallback(async () => {
    setConnecting(true);
    setError(null);
    try {
      await wc.connect();
    } catch (e: any) {
      const msg = e?.message || String(e);
      if (!msg.includes('User rejected') && !msg.includes('rejected')) {
        setError(msg);
      }
    } finally {
      setConnecting(false);
    }
  }, []);

  const disconnect = useCallback(async () => {
    await wc.disconnect();
  }, []);

  const signTransaction = useCallback(async (wcTransaction: string) => {
    return wc.signTransaction(wcTransaction);
  }, []);

  return (
    <WalletContext.Provider
      value={{ connected, address, connecting, error, connect, disconnect, signTransaction }}
    >
      {children}
    </WalletContext.Provider>
  );
}

export function useWallet() {
  return useContext(WalletContext);
}
