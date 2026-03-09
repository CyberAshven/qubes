/**
 * WalletConnect Context — Multi-Session
 *
 * Tracks multiple wallet sessions and provides per-qube session lookup.
 * Each session can have its public key recovered for qube-to-wallet matching.
 *
 * - `sessions`: all active WC sessions
 * - `connected` / `address` / `publicKey`: convenience getters for the active session
 * - `getSessionForQube(ownerPubkey)`: find the session matching a qube's owner
 * - `signTransactionWith(topic, wcTx)`: sign using a specific session
 */

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import * as wc from '../services/walletConnect';
import { recoverCompressedPubkey } from '../utils/recoverPublicKey';

export interface WalletSession extends wc.WcSession {
  publicKey?: string;
  publicKeySource?: 'wallet' | 'recovered';
}

interface WalletState {
  // All connected sessions (with pubkeys)
  sessions: WalletSession[];

  // Convenience: is ANY session connected?
  connected: boolean;
  // Active session address (first session)
  address: string | null;
  // Active session pubkey (first session)
  publicKey: string | null;
  publicKeySource: 'wallet' | 'recovered' | null;
  recoveringPubkey: boolean;
  connecting: boolean;
  wcUri: string | null;
  error: string | null;

  // Session management
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  disconnectSession: (topic: string) => Promise<void>;

  // Per-qube session lookup
  getSessionForQube: (ownerPubkey: string | undefined) => WalletSession | null;

  // Sign with a specific session (or default)
  signTransaction: (wcTransaction: string) => Promise<wc.WcSignResult>;
  signTransactionWith: (topic: string, wcTransaction: string) => Promise<wc.WcSignResult>;
  signMessage: (message: string, userPrompt?: string) => Promise<string>;
  getTokens: () => Promise<any[] | null>;
  getBalance: () => Promise<{ confirmed: number; unconfirmed?: number } | null>;
}

const WalletContext = createContext<WalletState>({
  sessions: [],
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
  disconnectSession: async () => {},
  getSessionForQube: () => null,
  signTransaction: async () => ({ signedTransaction: '', signedTransactionHash: '' }),
  signTransactionWith: async () => ({ signedTransaction: '', signedTransactionHash: '' }),
  signMessage: async () => '',
  getTokens: async () => null,
  getBalance: async () => null,
});

export function WalletProvider({ children }: { children: React.ReactNode }) {
  const [sessions, setSessions] = useState<WalletSession[]>([]);
  const [connecting, setConnecting] = useState(false);
  const [wcUri, setWcUri] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recoveringPubkey, setRecoveringPubkey] = useState(false);

  // Track which sessions we've attempted pubkey recovery on
  const recoveredTopicsRef = useRef<Set<string>>(new Set());
  // Track fresh connections (vs session restore)
  const freshTopicsRef = useRef<Set<string>>(new Set());

  // Listen for session changes from the service
  useEffect(() => {
    const unsub = wc.onSessionsChange((wcSessions) => {
      setSessions((prev) => {
        // Merge: keep existing pubkeys, add new sessions, remove deleted ones
        const prevMap = new Map(prev.map((s) => [s.topic, s]));
        return wcSessions.map((s) => ({
          ...s,
          publicKey: prevMap.get(s.topic)?.publicKey,
          publicKeySource: prevMap.get(s.topic)?.publicKeySource,
        }));
      });
    });

    // Check for existing sessions synchronously
    const existing = wc.getAllSessions();
    if (existing.length > 0) {
      setSessions(existing.map((s) => ({ ...s })));
    }

    // Eagerly initialize to restore sessions from storage
    wc.initClient().catch(() => {});

    return unsub;
  }, []);

  // Recover public keys for sessions that don't have them yet
  useEffect(() => {
    if (sessions.length === 0) return;

    const recoverPubkeys = async () => {
      for (const session of sessions) {
        if (session.publicKey) continue;
        if (recoveredTopicsRef.current.has(session.topic)) continue;
        recoveredTopicsRef.current.add(session.topic);

        // Step 1: Try bch_getAddresses
        try {
          const addrs = await wc.getAddresses(session.topic);
          const withPubkey = addrs.find((a) => a.publicKey);
          if (withPubkey?.publicKey) {
            setSessions((prev) =>
              prev.map((s) =>
                s.topic === session.topic
                  ? { ...s, publicKey: withPubkey.publicKey, publicKeySource: 'wallet' as const }
                  : s
              )
            );
            continue;
          }
        } catch {
          // Wallet doesn't support getAddresses
        }

        // Step 2: Recover from signMessage (fresh connections only)
        if (!freshTopicsRef.current.has(session.topic)) continue;
        setRecoveringPubkey(true);
        try {
          const message = `Qubes identity verification: ${session.address}`;
          const signatureBase64 = await wc.signMessage(
            message,
            'Verify your identity for Qube creation',
            session.topic,
          );
          const recovered = recoverCompressedPubkey(message, signatureBase64);
          if (/^(02|03)[a-fA-F0-9]{64}$/.test(recovered)) {
            setSessions((prev) =>
              prev.map((s) =>
                s.topic === session.topic
                  ? { ...s, publicKey: recovered, publicKeySource: 'recovered' as const }
                  : s
              )
            );
          }
        } catch {
          // User rejected or wallet doesn't support signMessage
        } finally {
          setRecoveringPubkey(false);
        }
      }
    };

    recoverPubkeys();
  }, [sessions.length]);

  const connectWallet = useCallback(async () => {
    setConnecting(true);
    setError(null);
    setWcUri(null);
    try {
      const session = await wc.connect((uri) => setWcUri(uri));
      freshTopicsRef.current.add(session.topic);
      setWcUri(null);
    } catch (e: any) {
      setWcUri(null);
      const msg = e?.message || String(e);
      if (!msg.includes('User rejected') && !msg.includes('rejected')) {
        setError(msg);
      }
    } finally {
      setConnecting(false);
    }
  }, []);

  const disconnectAll = useCallback(async () => {
    await wc.disconnectAll();
    recoveredTopicsRef.current.clear();
    freshTopicsRef.current.clear();
    setWcUri(null);
  }, []);

  const disconnectOne = useCallback(async (topic: string) => {
    await wc.disconnectSession(topic);
    recoveredTopicsRef.current.delete(topic);
    freshTopicsRef.current.delete(topic);
  }, []);

  // Find the session that owns a specific qube (by matching pubkey)
  const getSessionForQube = useCallback(
    (ownerPubkey: string | undefined): WalletSession | null => {
      if (!ownerPubkey) return null;
      return sessions.find((s) => s.publicKey === ownerPubkey) || null;
    },
    [sessions],
  );

  const signTransaction = useCallback(async (wcTransaction: string) => {
    return wc.signTransaction(wcTransaction);
  }, []);

  const signTransactionWith = useCallback(async (topic: string, wcTransaction: string) => {
    return wc.signTransaction(wcTransaction, topic);
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

  // Convenience getters from first session
  const firstSession = sessions[0] || null;

  return (
    <WalletContext.Provider
      value={{
        sessions,
        connected: sessions.length > 0,
        address: firstSession?.address || null,
        publicKey: firstSession?.publicKey || null,
        publicKeySource: firstSession?.publicKeySource || null,
        recoveringPubkey,
        connecting,
        wcUri,
        error,
        connect: connectWallet,
        disconnect: disconnectAll,
        disconnectSession: disconnectOne,
        getSessionForQube,
        signTransaction,
        signTransactionWith,
        signMessage,
        getTokens,
        getBalance,
      }}
    >
      {children}
    </WalletContext.Provider>
  );
}

export function useWallet() {
  return useContext(WalletContext);
}
