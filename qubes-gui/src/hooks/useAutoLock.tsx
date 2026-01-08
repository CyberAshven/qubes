import { useEffect, useRef, useCallback } from 'react';
import { useAuth } from './useAuth';

/**
 * Hook that monitors user activity and locks the app after a period of inactivity.
 * Activity is detected via mouse movement, keyboard input, clicks, and touch events.
 */
export const useAutoLock = () => {
  const {
    isAuthenticated,
    isLocked,
    autoLockEnabled,
    autoLockTimeout,
    lock
  } = useAuth();

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastActivityRef = useRef<number>(Date.now());

  // Reset the inactivity timer
  const resetTimer = useCallback(() => {
    lastActivityRef.current = Date.now();

    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    // Only set timer if auto-lock is enabled and user is authenticated but not locked
    if (autoLockEnabled && isAuthenticated && !isLocked) {
      const timeoutMs = autoLockTimeout * 60 * 1000; // Convert minutes to ms
      timerRef.current = setTimeout(() => {
        lock();
      }, timeoutMs);
    }
  }, [autoLockEnabled, autoLockTimeout, isAuthenticated, isLocked, lock]);

  // Activity event handler
  const handleActivity = useCallback(() => {
    if (isAuthenticated && !isLocked) {
      resetTimer();
    }
  }, [isAuthenticated, isLocked, resetTimer]);

  useEffect(() => {
    // Don't set up listeners if not authenticated or already locked
    if (!isAuthenticated || isLocked || !autoLockEnabled) {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      return;
    }

    // Events to track for activity
    const events = [
      'mousedown',
      'mousemove',
      'keydown',
      'scroll',
      'touchstart',
      'click',
      'wheel'
    ];

    // Throttle to prevent excessive timer resets
    let lastEventTime = 0;
    const throttledHandler = () => {
      const now = Date.now();
      if (now - lastEventTime > 1000) { // Max once per second
        lastEventTime = now;
        handleActivity();
      }
    };

    // Add event listeners
    events.forEach(event => {
      window.addEventListener(event, throttledHandler, { passive: true });
    });

    // Start the initial timer
    resetTimer();

    // Cleanup
    return () => {
      events.forEach(event => {
        window.removeEventListener(event, throttledHandler);
      });
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [isAuthenticated, isLocked, autoLockEnabled, handleActivity, resetTimer]);

  return {
    resetTimer,
    lastActivity: lastActivityRef.current,
  };
};

export default useAutoLock;
