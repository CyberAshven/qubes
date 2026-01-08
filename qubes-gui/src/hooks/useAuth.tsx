import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { NftAuthToken } from '../types';

interface AuthState {
  isAuthenticated: boolean;
  isLocked: boolean;
  userId: string | null;
  dataDir: string | null;
  password: string | null;
  // Auto-lock settings
  autoLockEnabled: boolean;
  autoLockTimeout: number; // minutes
  // NFT Authentication tokens per Qube
  nftTokens: Record<string, NftAuthToken>;
  login: (userId: string, dataDir: string, password: string) => void;
  logout: () => void;
  lock: () => void;
  unlock: (password: string) => boolean;
  setAutoLockSettings: (enabled: boolean, timeout: number) => void;
  // NFT Auth methods
  setNftToken: (qubeId: string, token: string, expiresAt: number) => void;
  getNftToken: (qubeId: string) => NftAuthToken | null;
  clearNftToken: (qubeId: string) => void;
  clearAllNftTokens: () => void;
  isNftTokenValid: (qubeId: string) => boolean;
}

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => ({
      isAuthenticated: false,
      isLocked: false,
      userId: null,
      dataDir: null,
      password: null,
      autoLockEnabled: true,
      autoLockTimeout: 5, // 5 minutes default
      nftTokens: {},

      login: (userId: string, dataDir: string, password: string) =>
        set({ isAuthenticated: true, isLocked: false, userId, dataDir, password }),

      logout: () =>
        set({
          isAuthenticated: false,
          isLocked: false,
          userId: null,
          dataDir: null,
          password: null,
          nftTokens: {}  // Clear all NFT tokens on logout
        }),

      lock: () => set({ isLocked: true }),

      unlock: (enteredPassword: string) => {
        const state = get();
        if (enteredPassword === state.password) {
          set({ isLocked: false });
          return true;
        }
        return false;
      },

      setAutoLockSettings: (enabled: boolean, timeout: number) =>
        set({ autoLockEnabled: enabled, autoLockTimeout: timeout }),

      setNftToken: (qubeId: string, token: string, expiresAt: number) =>
        set((state) => ({
          nftTokens: {
            ...state.nftTokens,
            [qubeId]: { qube_id: qubeId, token, expires_at: expiresAt }
          }
        })),

      getNftToken: (qubeId: string) => {
        const state = get();
        return state.nftTokens[qubeId] || null;
      },

      clearNftToken: (qubeId: string) =>
        set((state) => {
          const { [qubeId]: _, ...rest } = state.nftTokens;
          return { nftTokens: rest };
        }),

      clearAllNftTokens: () =>
        set({ nftTokens: {} }),

      isNftTokenValid: (qubeId: string) => {
        const state = get();
        const token = state.nftTokens[qubeId];
        if (!token) return false;
        // Check if token is expired (with 60 second buffer)
        const now = Math.floor(Date.now() / 1000);
        return token.expires_at > (now + 60);
      },
    }),
    {
      name: 'qubes-auth-storage',
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
        isLocked: state.isLocked,
        userId: state.userId,
        dataDir: state.dataDir,
        password: state.password,  // Include password for session (sessionStorage clears on browser close)
        autoLockEnabled: state.autoLockEnabled,
        autoLockTimeout: state.autoLockTimeout,
        nftTokens: state.nftTokens,  // Persist NFT tokens (session storage clears on close)
      }),
    }
  )
);
