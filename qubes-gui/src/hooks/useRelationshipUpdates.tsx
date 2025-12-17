import { useEffect, useRef, useCallback, useState } from 'react';

interface RelationshipUpdate {
  type: 'relationship_updated' | 'relationship_progressed' | 'best_friend_changed' | 'connection_established';
  timestamp: string;
  data?: {
    qube_id?: string;
    entity_id?: string;
    relationship?: any;
    old_status?: string;
    new_status?: string;
    trust_score?: number;
    old_best_friend?: string;
    new_best_friend?: string;
  };
  message?: string;
}

interface UseRelationshipUpdatesOptions {
  onUpdate?: (update: RelationshipUpdate) => void;
  autoConnect?: boolean;
  reconnectDelay?: number;
}

/**
 * Hook for receiving real-time relationship updates via WebSocket
 *
 * @param options - Configuration options
 * @returns Object with connection status and manual connect/disconnect functions
 */
export const useRelationshipUpdates = (options: UseRelationshipUpdatesOptions = {}) => {
  const {
    onUpdate,
    autoConnect = true,
    reconnectDelay = 3000,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<RelationshipUpdate | null>(null);

  const connect = useCallback(() => {
    // Clean up existing connection
    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch (e) {
        console.warn('[WS] Error closing existing connection:', e);
      }
      wsRef.current = null;
    }

    try {
      // Connect to WebSocket server
      const ws = new WebSocket('ws://localhost:8765');

      ws.onopen = () => {
        console.log('[WS] Connected to relationship updates');
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const update: RelationshipUpdate = JSON.parse(event.data);
          console.log('[WS] Received update:', update);

          setLastUpdate(update);

          if (onUpdate) {
            onUpdate(update);
          }
        } catch (error) {
          console.error('[WS] Failed to parse message:', error);
        }
      };

      ws.onerror = (error) => {
        console.warn('[WS] Connection error (server may not be running):', error);
      };

      ws.onclose = () => {
        console.log('[WS] Disconnected from relationship updates');
        setIsConnected(false);
        wsRef.current = null;

        // Attempt to reconnect after delay (only if autoConnect is true)
        if (autoConnect) {
          console.log(`[WS] Reconnecting in ${reconnectDelay}ms...`);
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectDelay);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.warn('[WS] Failed to create WebSocket (server may not be running):', error);
      setIsConnected(false);
    }
  }, [onUpdate, autoConnect, reconnectDelay]);

  const disconnect = useCallback(() => {
    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Close WebSocket connection
    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch (e) {
        console.warn('[WS] Error closing connection:', e);
      }
      wsRef.current = null;
    }

    setIsConnected(false);
  }, []);

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    // Cleanup on unmount
    return () => {
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoConnect]); // Only depend on autoConnect, not connect/disconnect (they're stable)

  return {
    isConnected,
    lastUpdate,
    connect,
    disconnect,
  };
};
