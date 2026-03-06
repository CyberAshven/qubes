/**
 * WalletConnect Context
 *
 * Provides wallet connection state to the entire app.
 * Wraps the walletConnect service with React state management.
 *
 * After connection, auto-retrieves the user's compressed public key:
 * 1. Try bch_getAddresses (some wallets include publicKey)
 * 2. Fallback: bch_signMessage + secp256k1 recovery
 */

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import * as wc from '../services/walletConnect';
import { recoverCompressedPubkey } from '../utils/recoverPublicKey';

interface WalletState {
  connected: boolean;
  address: string | null;
  publicKey: string | null;
  publicKeySource: 'wallet' | 'recovered' | null;
  recoveringPubkey: boolean;
  connecting: boolean;
  wcUri: string | null;
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
  publicKeySource: null,
  recoveringPubkey: false,
  connecting: false,
  wcUri: null,
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
  const [publicKeySource, setPublicKeySource] = useState<'wallet' | 'recovered' | null>(null);
  const [recoveringPubkey, setRecoveringPubkey] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [wcUri, setWcUri] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Track whether this is a fresh connection (vs session restore)
  const freshConnectionRef = useRef(false);

  // Listen for session changes (including restored sessions)
  useEffect(() => {
    const unsub = wc.onSessionChange((session) => {
      if (session) {
        setConnected(true);
        setAddress(session.address);
        setWcUri(null); // Clear URI once connected
      } else {
        setConnected(false);
        setAddress(null);
        setPublicKey(null);
        setPublicKeySource(null);
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

  // When connected, try to fetch the public key:
  // 1. bch_getAddresses (some wallets include publicKey)
  // 2. bch_signMessage + recovery (only on fresh connections)
  useEffect(() => {
    if (!connected || !address) return;
    let cancelled = false;

    (async () => {
      // Step 1: Try bch_getAddresses
      try {
        const addrs = await wc.getAddresses();
        if (cancelled) return;
        const withPubkey = addrs.find((a) => a.publicKey);
        if (withPubkey?.publicKey) {
          setPublicKey(withPubkey.publicKey);
          setPublicKeySource('wallet');
          return;
        }
      } catch {
        // Wallet doesn't support getAddresses
      }

      // Step 2: Recover pubkey from signMessage (fresh connections only)
      if (cancelled || !freshConnectionRef.current) return;
      setRecoveringPubkey(true);
      try {
        const message = `Qubes identity verification: ${address}`;
        const signatureBase64 = await wc.signMessage(
          message,
          'Verify your identity for Qube creation',
        );
        if (cancelled) return;
        const recovered = recoverCompressedPubkey(message, signatureBase64);
        if (/^(02|03)[a-fA-F0-9]{64}$/.test(recovered)) {
          setPublicKey(recovered);
          setPublicKeySource('recovered');
        }
      } catch {
        // User rejected or wallet doesn't support signMessage — manual entry
      } finally {
        if (!cancelled) setRecoveringPubkey(false);
      }
    })();

    return () => { cancelled = true; };
  }, [connected, address]);

  const connect = useCallback(async () => {
    setConnecting(true);
    setError(null);
    setWcUri(null);
    freshConnectionRef.current = true;
    try {
      await wc.connect((uri) => setWcUri(uri));
      setWcUri(null);
    } catch (e: any) {
      freshConnectionRef.current = false;
      setWcUri(null);
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
    setPublicKeySource(null);
    setRecoveringPubkey(false);
    setWcUri(null);
    freshConnectionRef.current = false;
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
      value={{
        connected, address, publicKey, publicKeySource, recoveringPubkey,
        connecting, wcUri, error, connect, disconnect, signTransaction, signMessage,
        getTokens, getBalance,
      }}
    >
      {children}
    </WalletContext.Provider>
  );
}

export function useWallet() {
  return useContext(WalletContext);
}
