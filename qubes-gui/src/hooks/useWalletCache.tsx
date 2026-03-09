import { create } from 'zustand';
import { TransactionHistoryEntry } from '../types';

interface WalletData {
  balance: number | null;
  transactions: TransactionHistoryEntry[];
  totalTxCount: number;
  hasMoreTx: boolean;
  lastFetched: number; // timestamp
  error: string | null;
}

interface WalletCacheState {
  // Wallet data keyed by qubeId
  wallets: Record<string, WalletData>;

  // Get cached wallet data for a qube
  getWalletData: (qubeId: string) => WalletData | null;

  // Set balance for a qube
  setBalance: (qubeId: string, balance: number) => void;

  // Set transactions for a qube
  setTransactions: (
    qubeId: string,
    transactions: TransactionHistoryEntry[],
    totalCount: number,
    hasMore: boolean,
    append?: boolean
  ) => void;

  // Set error for a qube
  setError: (qubeId: string, error: string | null) => void;

  // Invalidate cache for a qube (e.g., after sending a transaction)
  invalidateCache: (qubeId: string) => void;

  // Invalidate all caches
  invalidateAllCaches: () => void;

  // Check if cache is stale (older than maxAge in ms)
  isCacheStale: (qubeId: string, maxAge?: number) => boolean;
}

const DEFAULT_CACHE_MAX_AGE = 5 * 60 * 1000; // 5 minutes

const createEmptyWalletData = (): WalletData => ({
  balance: null,
  transactions: [],
  totalTxCount: 0,
  hasMoreTx: false,
  lastFetched: 0,
  error: null,
});

export const useWalletCache = create<WalletCacheState>((set, get) => ({
  wallets: {},

  getWalletData: (qubeId: string) => {
    return get().wallets[qubeId] || null;
  },

  setBalance: (qubeId: string, balance: number) => {
    set((state) => ({
      wallets: {
        ...state.wallets,
        [qubeId]: {
          ...(state.wallets[qubeId] || createEmptyWalletData()),
          balance,
          lastFetched: Date.now(),
          error: null,
        },
      },
    }));
  },

  setTransactions: (
    qubeId: string,
    transactions: TransactionHistoryEntry[],
    totalCount: number,
    hasMore: boolean,
    append: boolean = false
  ) => {
    set((state) => {
      const existing = state.wallets[qubeId] || createEmptyWalletData();
      return {
        wallets: {
          ...state.wallets,
          [qubeId]: {
            ...existing,
            transactions: append
              ? [...existing.transactions, ...transactions]
              : transactions,
            totalTxCount: totalCount,
            hasMoreTx: hasMore,
            lastFetched: Date.now(),
            error: null,
          },
        },
      };
    });
  },

  setError: (qubeId: string, error: string | null) => {
    set((state) => ({
      wallets: {
        ...state.wallets,
        [qubeId]: {
          ...(state.wallets[qubeId] || createEmptyWalletData()),
          error,
        },
      },
    }));
  },

  invalidateCache: (qubeId: string) => {
    set((state) => {
      const { [qubeId]: _, ...rest } = state.wallets;
      return { wallets: rest };
    });
  },

  invalidateAllCaches: () => {
    set({ wallets: {} });
  },

  isCacheStale: (qubeId: string, maxAge: number = DEFAULT_CACHE_MAX_AGE) => {
    const wallet = get().wallets[qubeId];
    if (!wallet || wallet.lastFetched === 0) return true;
    return Date.now() - wallet.lastFetched > maxAge;
  },
}));

export default useWalletCache;
