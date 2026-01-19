import React, { createContext, useContext, useRef, useCallback, useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen, UnlistenFn } from '@tauri-apps/api/event';
import { useAuth } from '../hooks/useAuth';

// Cache entry for a single qube's chain state
interface ChainStateCacheEntry {
  data: any;
  hash: string;
  timestamp: number;
}

// Event payload from backend
interface ChainStateEventPayload {
  type: string;
  qube_id: string;
  event_type: string;
  payload: Record<string, any>;
  timestamp: number;
  source: string;
}

interface ChainStateContextType {
  // Get cached chain state for a qube (returns null if not cached)
  getChainState: (qubeId: string) => any | null;

  // Load chain state for a qube (uses cache if valid, fetches if not)
  loadChainState: (qubeId: string, forceRefresh?: boolean) => Promise<any>;

  // Invalidate cache for a qube (forces next load to fetch fresh data)
  invalidateCache: (qubeId: string) => void;

  // Update cache immediately with new data (for local changes)
  updateCache: (qubeId: string, data: any) => void;

  // Check if data is loading for a qube
  isLoading: (qubeId: string) => boolean;

  // Start watching events for a qube
  startWatching: (qubeId: string) => Promise<void>;

  // Stop watching events for a qube
  stopWatching: (qubeId: string) => Promise<void>;

  // Cache version - increments when cache is updated, useful for triggering effects
  cacheVersion: number;

  // Last event received (for debugging/UI feedback)
  lastEvent: ChainStateEventPayload | null;
}

const ChainStateContext = createContext<ChainStateContextType | undefined>(undefined);

export const useChainState = () => {
  const context = useContext(ChainStateContext);
  if (!context) {
    throw new Error('useChainState must be used within ChainStateProvider');
  }
  return context;
};

// Refresh interval in milliseconds (60 seconds) - fallback if events fail
const REFRESH_INTERVAL = 60000;

// Cache is considered stale after this time (55 seconds - slightly less than refresh)
const CACHE_STALE_TIME = 55000;

export const ChainStateProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { userId, password } = useAuth();

  // Cache storage: qubeId -> cache entry
  const cacheRef = useRef<Map<string, ChainStateCacheEntry>>(new Map());

  // Version counter to trigger re-renders when cache is updated
  // Components that call getChainState will re-render when this changes
  const [cacheVersion, setCacheVersion] = useState(0);

  // Loading state per qube
  const [loadingQubes, setLoadingQubes] = useState<Set<string>>(new Set());

  // Track which qubes are actively being used (for periodic refresh)
  const activeQubesRef = useRef<Set<string>>(new Set());

  // Track which qubes have active event watchers
  const watchingQubesRef = useRef<Set<string>>(new Set());

  // Last event received (for debugging)
  const [lastEvent, setLastEvent] = useState<ChainStateEventPayload | null>(null);

  // Event listener cleanup function
  const unlistenRef = useRef<UnlistenFn | null>(null);

  // Fetch chain state from backend
  const fetchChainState = useCallback(async (qubeId: string): Promise<{ data: any; hash: string } | null> => {
    if (!userId || !password) return null;

    try {
      const result = await invoke<any>('get_context_preview', {
        userId,
        qubeId,
        password,
      });

      if (!result.success) {
        console.error('Failed to fetch chain state:', result.error);
        return null;
      }

      return {
        data: {
          active_context: result.active_context,
          short_term_memory: result.short_term_memory,
        },
        hash: result.content_hash || '',
      };
    } catch (error) {
      console.error('Error fetching chain state:', error);
      return null;
    }
  }, [userId, password]);

  // Get cached chain state (returns null if not cached or stale)
  const getChainState = useCallback((qubeId: string): any | null => {
    const entry = cacheRef.current.get(qubeId);
    if (!entry) return null;

    // Mark this qube as active
    activeQubesRef.current.add(qubeId);

    return entry.data;
  }, []);

  // Load chain state with caching
  const loadChainState = useCallback(async (qubeId: string, forceRefresh = false): Promise<any> => {
    // Mark this qube as active
    activeQubesRef.current.add(qubeId);

    const cached = cacheRef.current.get(qubeId);
    const now = Date.now();

    // Return cached data immediately if available and not forcing refresh
    if (cached && !forceRefresh) {
      // If cache is still fresh, just return it
      if (now - cached.timestamp < CACHE_STALE_TIME) {
        return cached.data;
      }
    }

    // Check if already loading
    if (loadingQubes.has(qubeId)) {
      // Return cached data while loading, or null
      return cached?.data || null;
    }

    // Start loading
    setLoadingQubes(prev => new Set(prev).add(qubeId));

    try {
      const result = await fetchChainState(qubeId);

      if (result) {
        // Only update cache if hash changed or no previous cache
        if (!cached || cached.hash !== result.hash || forceRefresh) {
          cacheRef.current.set(qubeId, {
            data: result.data,
            hash: result.hash,
            timestamp: now,
          });
          // Trigger re-render for components using the cache
          setCacheVersion(v => v + 1);
        } else {
          // Just update timestamp if hash unchanged
          cacheRef.current.set(qubeId, {
            ...cached,
            timestamp: now,
          });
        }

        return result.data;
      }

      // Return cached data if fetch failed
      return cached?.data || null;
    } finally {
      setLoadingQubes(prev => {
        const next = new Set(prev);
        next.delete(qubeId);
        return next;
      });
    }
  }, [fetchChainState, loadingQubes]);

  // Invalidate cache for a qube
  const invalidateCache = useCallback((qubeId: string) => {
    cacheRef.current.delete(qubeId);
    // Trigger re-render so components know cache was invalidated
    setCacheVersion(v => v + 1);
  }, []);

  // Update cache immediately (for local changes)
  const updateCache = useCallback((qubeId: string, data: any) => {
    const existing = cacheRef.current.get(qubeId);
    cacheRef.current.set(qubeId, {
      data,
      hash: existing?.hash || 'local-update',
      timestamp: Date.now(),
    });
    // Trigger re-render for components using the cache
    setCacheVersion(v => v + 1);
  }, []);

  // Check if loading
  const isLoading = useCallback((qubeId: string): boolean => {
    return loadingQubes.has(qubeId);
  }, [loadingQubes]);

  // Start watching events for a qube
  const startWatching = useCallback(async (qubeId: string) => {
    if (!userId || !password) return;

    // Already watching this qube
    if (watchingQubesRef.current.has(qubeId)) return;

    try {
      await invoke('start_event_watcher_cmd', {
        userId,
        qubeId,
        password,
      });
      watchingQubesRef.current.add(qubeId);
      console.log(`[ChainState] Started watching events for qube ${qubeId}`);
    } catch (error) {
      console.error(`[ChainState] Failed to start event watcher for ${qubeId}:`, error);
    }
  }, [userId, password]);

  // Stop watching events for a qube
  const stopWatching = useCallback(async (qubeId: string) => {
    if (!userId) return;

    if (!watchingQubesRef.current.has(qubeId)) return;

    try {
      await invoke('stop_event_watcher_cmd', {
        userId,
        qubeId,
      });
      watchingQubesRef.current.delete(qubeId);
      console.log(`[ChainState] Stopped watching events for qube ${qubeId}`);
    } catch (error) {
      console.error(`[ChainState] Failed to stop event watcher for ${qubeId}:`, error);
    }
  }, [userId]);

  // Handle incoming chain state events
  const handleChainStateEvent = useCallback((event: ChainStateEventPayload) => {
    console.log('[ChainState] Received event:', event.event_type, 'for qube:', event.qube_id);
    setLastEvent(event);

    // Invalidate cache for this qube to force refresh
    // This is the simplest approach - more sophisticated handling could update cache directly
    const qubeId = event.qube_id;
    if (qubeId) {
      invalidateCache(qubeId);

      // Optionally trigger immediate refresh if this qube is active
      if (activeQubesRef.current.has(qubeId)) {
        fetchChainState(qubeId).then(result => {
          if (result) {
            cacheRef.current.set(qubeId, {
              data: result.data,
              hash: result.hash,
              timestamp: Date.now(),
            });
            setCacheVersion(v => v + 1);
          }
        });
      }
    }
  }, [invalidateCache, fetchChainState]);

  // Set up event listener on mount
  useEffect(() => {
    let mounted = true;

    const setupListener = async () => {
      try {
        const unlisten = await listen<ChainStateEventPayload>('chain-state-event', (event) => {
          if (mounted) {
            handleChainStateEvent(event.payload);
          }
        });
        unlistenRef.current = unlisten;
        console.log('[ChainState] Event listener set up');
      } catch (error) {
        console.error('[ChainState] Failed to set up event listener:', error);
      }
    };

    setupListener();

    return () => {
      mounted = false;
      if (unlistenRef.current) {
        unlistenRef.current();
        unlistenRef.current = null;
      }
    };
  }, [handleChainStateEvent]);

  // Periodic refresh for active qubes (fallback if events fail)
  useEffect(() => {
    if (!userId || !password) return;

    const intervalId = setInterval(async () => {
      // Refresh all active qubes
      const activeQubes = Array.from(activeQubesRef.current);

      for (const qubeId of activeQubes) {
        const cached = cacheRef.current.get(qubeId);
        const now = Date.now();

        // Only refresh if cache is stale
        if (!cached || now - cached.timestamp >= CACHE_STALE_TIME) {
          // Don't await - let them run in parallel
          fetchChainState(qubeId).then(result => {
            if (result) {
              const existing = cacheRef.current.get(qubeId);
              if (!existing || existing.hash !== result.hash) {
                cacheRef.current.set(qubeId, {
                  data: result.data,
                  hash: result.hash,
                  timestamp: Date.now(),
                });
                setCacheVersion(v => v + 1);
              } else {
                cacheRef.current.set(qubeId, {
                  ...existing,
                  timestamp: Date.now(),
                });
              }
            }
          });
        }
      }
    }, REFRESH_INTERVAL);

    return () => clearInterval(intervalId);
  }, [userId, password, fetchChainState]);

  // Clear active qubes and stop watchers when user changes
  useEffect(() => {
    // Stop all watchers
    const stopAll = async () => {
      const watching = Array.from(watchingQubesRef.current);
      for (const qubeId of watching) {
        try {
          await invoke('stop_event_watcher_cmd', { userId, qubeId });
        } catch {
          // Ignore errors during cleanup
        }
      }
      watchingQubesRef.current.clear();
    };

    return () => {
      stopAll();
      activeQubesRef.current.clear();
      cacheRef.current.clear();
    };
  }, [userId]);

  const value: ChainStateContextType = {
    getChainState,
    loadChainState,
    invalidateCache,
    updateCache,
    isLoading,
    startWatching,
    stopWatching,
    cacheVersion,
    lastEvent,
  };

  return (
    <ChainStateContext.Provider value={value}>
      {children}
    </ChainStateContext.Provider>
  );
};
