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
  publicKey: string | null;
  connecting: boolean;
  error: string | null;
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  signTransaction: (wcTransaction: string) => Promise<wc.WcSignResult>;
  signMessage: (message: string, userPrompt?: string) => Promise<string>;
  getTokens: () => Promise<any[] | null>;
  getBalance: () => Promise<{ confirmed: number; unconfirmed?: number } | null>;
}

const WalletContext = createContext<WalletState>({
  connected: false,
  address: null,
  publicKey: null,
  connecting: false,
  error: null,
  connect: async () => {},
  disconnect: async () => {},
  signTransaction: async () => ({ signedTransaction: '', signedTransactionHash: '' }),
  signMessage: async () => '',
  getTokens: async () => null,
  getBalance: async () => null,
});

export function WalletProvider({ children }: { children: React.ReactNode }) {
  const [connected, setConnected] = useState(false);
  const [address, setAddress] = useState<string | null>(null);
  const [publicKey, setPublicKey] = useState<string | null>(null);
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
        setPublicKey(null);
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

  // When connected, try to fetch the public key via bch_getAddresses
  useEffect(() => {
    if (!connected) return;
    let cancelled = false;
    (async () => {
      try {
        const addrs = await wc.getAddresses();
        if (cancelled) return;
        // Look for a publicKey in the response
        const withPubkey = addrs.find((a) => a.publicKey);
        if (withPubkey?.publicKey) {
          setPublicKey(withPubkey.publicKey);
        }
      } catch {
        // Wallet doesn't support getAddresses — that's fine
      }
    })();
    return () => { cancelled = true; };
  }, [connected]);

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
    setPublicKey(null);
  }, []);

  const signTransaction = useCallback(async (wcTransaction: string) => {
    return wc.signTransaction(wcTransaction);
  }, []);

  const signMessage = useCallback(async (message: string, userPrompt?: string) => {
    return wc.signMessage(message, userPrompt);
  }, []);

  const getTokens = useCallback(async () => {
    return wc.getTokens();
  }, []);

  const getBalance = useCallback(async () => {
    return wc.getBalance();
  }, []);

  return (
    <WalletContext.Provider
      value={{ connected, address, publicKey, connecting, error, connect, disconnect, signTransaction, signMessage, getTokens, getBalance }}
    >
      {children}
    </WalletContext.Provider>
  );
}

export function useWallet() {
  return useContext(WalletContext);
}
