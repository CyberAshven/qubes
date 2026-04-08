import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { NftAuthToken } from '../types';

// Load auto-lock settings from localStorage (persists across restarts)
const loadAutoLockSettings = () => {
  try {
    const saved = localStorage.getItem('qubes-autolock-settings');
    if (saved) {
      const parsed = JSON.parse(saved);
      return {
        autoLockEnabled: parsed.autoLockEnabled ?? false,
        autoLockTimeout: parsed.autoLockTimeout ?? 15,
      };
    }
  } catch (e) {
    console.error('Failed to load auto-lock settings:', e);
  }
  return { autoLockEnabled: false, autoLockTimeout: 15 };
};

// Save auto-lock settings to localStorage
const saveAutoLockSettings = (enabled: boolean, timeout: number) => {
  try {
    localStorage.setItem('qubes-autolock-settings', JSON.stringify({
      autoLockEnabled: enabled,
      autoLockTimeout: timeout,
    }));
  } catch (e) {
    console.error('Failed to save auto-lock settings:', e);
  }
};

const initialAutoLock = loadAutoLockSettings();

// Load remember-login settings from localStorage (persists across restarts)
const REMEMBER_LOGIN_KEY = 'qubes-remember-login';
const SAVED_CREDENTIALS_KEY = 'qubes-saved-credentials';

const loadRememberLoginSettings = () => {
  try {
    const saved = localStorage.getItem(REMEMBER_LOGIN_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      return {
        rememberUsername: parsed.rememberUsername ?? false,
        rememberPassword: parsed.rememberPassword ?? false,
        autoLogin: parsed.autoLogin ?? false,
      };
    }
  } catch (e) {
    console.error('Failed to load remember-login settings:', e);
  }
  return { rememberUsername: false, rememberPassword: false, autoLogin: false };
};

const saveRememberLoginSettings = (rememberUsername: boolean, rememberPassword: boolean, autoLogin: boolean) => {
  try {
    localStorage.setItem(REMEMBER_LOGIN_KEY, JSON.stringify({ rememberUsername, rememberPassword, autoLogin }));
    // If disabling remember, clear saved credentials
    if (!rememberUsername && !rememberPassword) {
      localStorage.removeItem(SAVED_CREDENTIALS_KEY);
    } else if (!rememberUsername) {
      // Keep password setting but clear username
      const creds = JSON.parse(localStorage.getItem(SAVED_CREDENTIALS_KEY) || '{}');
      delete creds.username;
      localStorage.setItem(SAVED_CREDENTIALS_KEY, JSON.stringify(creds));
    } else if (!rememberPassword) {
      // Keep username but clear password
      const creds = JSON.parse(localStorage.getItem(SAVED_CREDENTIALS_KEY) || '{}');
      delete creds.password;
      localStorage.setItem(SAVED_CREDENTIALS_KEY, JSON.stringify(creds));
    }
  } catch (e) {
    console.error('Failed to save remember-login settings:', e);
  }
};

const saveCredentials = (username: string, password: string, rememberUsername: boolean, rememberPassword: boolean) => {
  try {
    const creds: Record<string, string> = {};
    if (rememberUsername) creds.username = username;
    if (rememberPassword) creds.password = password;
    if (Object.keys(creds).length > 0) {
      localStorage.setItem(SAVED_CREDENTIALS_KEY, JSON.stringify(creds));
    }
  } catch (e) {
    console.error('Failed to save credentials:', e);
  }
};

export const getSavedCredentials = (): { username?: string; password?: string } => {
  try {
    const settings = loadRememberLoginSettings();
    const saved = localStorage.getItem(SAVED_CREDENTIALS_KEY);
    if (!saved) return {};
    const creds = JSON.parse(saved);
    return {
      username: settings.rememberUsername ? creds.username : undefined,
      password: settings.rememberPassword ? creds.password : undefined,
    };
  } catch (e) {
    return {};
  }
};

const initialRememberLogin = loadRememberLoginSettings();

interface AuthState {
  isAuthenticated: boolean;
  isLocked: boolean;
  userId: string | null;
  dataDir: string | null;
  password: string | null;
  // Auto-lock settings
  autoLockEnabled: boolean;
  autoLockTimeout: number; // minutes
  // Remember login settings
  rememberUsername: boolean;
  rememberPassword: boolean;
  autoLogin: boolean;
  // NFT Authentication tokens per Qube
  nftTokens: Record<string, NftAuthToken>;
  login: (userId: string, dataDir: string, password: string) => void;
  logout: () => void;
  lock: () => void;
  unlock: (password: string) => boolean;
  setAutoLockSettings: (enabled: boolean, timeout: number) => void;
  setRememberLoginSettings: (rememberUsername: boolean, rememberPassword: boolean, autoLogin: boolean) => void;
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
      autoLockEnabled: initialAutoLock.autoLockEnabled,
      autoLockTimeout: initialAutoLock.autoLockTimeout,
      rememberUsername: initialRememberLogin.rememberUsername,
      rememberPassword: initialRememberLogin.rememberPassword,
      autoLogin: initialRememberLogin.autoLogin,
      nftTokens: {},

      login: (userId: string, dataDir: string, password: string) => {
        const state = get();
        saveCredentials(userId, password, state.rememberUsername, state.rememberPassword);
        set({ isAuthenticated: true, isLocked: false, userId, dataDir, password });
      },

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

      setAutoLockSettings: (enabled: boolean, timeout: number) => {
        saveAutoLockSettings(enabled, timeout);
        set({ autoLockEnabled: enabled, autoLockTimeout: timeout });
      },

      setRememberLoginSettings: (rememberUsername: boolean, rememberPassword: boolean, autoLogin: boolean) => {
        saveRememberLoginSettings(rememberUsername, rememberPassword, autoLogin);
        set({ rememberUsername, rememberPassword, autoLogin });
      },

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
