import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';

interface ModelModeIndicatorProps {
  qubeId: string | null;
  userId: string;
  password: string | null;
}

/**
 * Isolated Model Mode indicator component that manages its own state.
 * This prevents model mode updates from causing the entire TabContent to re-render,
 * which would break the typewriter effect during streaming.
 */
export const ModelModeIndicator: React.FC<ModelModeIndicatorProps> = ({ qubeId, userId, password }) => {
  const [modelMode, setModelMode] = useState<'manual' | 'revolver' | 'autonomous'>('manual');

  // Fetch model mode when qube changes
  useEffect(() => {
    const fetchModelMode = async () => {
      if (!qubeId || !userId || !password) {
        setModelMode('manual');
        return;
      }

      try {
        const result = await invoke<{
          success: boolean;
          model_locked?: boolean;
          revolver_mode?: boolean;
          autonomous_mode?: boolean;
          error?: string;
        }>('get_model_preferences', {
          userId,
          qubeId,
          password,
        });

        if (result.success) {
          if (result.revolver_mode) {
            setModelMode('revolver');
          } else if (result.autonomous_mode) {
            setModelMode('autonomous');
          } else {
            setModelMode('manual');
          }
        }
      } catch (err) {
        console.error('Failed to fetch model mode:', err);
        setModelMode('manual');
      }
    };

    fetchModelMode();
  }, [qubeId, userId, password]);

  // Listen for model mode changes from QubeSettingsModal
  useEffect(() => {
    const setupListener = async () => {
      const unlisten = await listen<{
        qubeId: string;
        modelLocked: boolean;
        revolverMode: boolean;
        autonomousMode: boolean;
      }>('model-mode-changed', (event) => {
        // Only update if the changed qube matches the selected qube
        if (qubeId && event.payload.qubeId === qubeId) {
          if (event.payload.revolverMode) {
            setModelMode('revolver');
          } else if (event.payload.autonomousMode) {
            setModelMode('autonomous');
          } else {
            setModelMode('manual');
          }
        }
      });
      return unlisten;
    };

    const cleanupPromise = setupListener();
    return () => {
      cleanupPromise.then(cleanup => cleanup());
    };
  }, [qubeId]);

  if (!qubeId) return null;

  return (
    <div className="flex items-center gap-2 whitespace-nowrap">
      <span className="text-text-secondary text-sm whitespace-nowrap">Model Mode:</span>
      <span
        className={`px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap flex items-center gap-1 ${
          modelMode === 'revolver'
            ? 'bg-green-500/20 text-green-400 border border-green-500/30'
            : modelMode === 'autonomous'
              ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
              : 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
        }`}
      >
        <span>{modelMode === 'revolver' ? '🎰' : modelMode === 'autonomous' ? '🤖' : '🔒'}</span>
        <span>{modelMode === 'revolver' ? 'Revolver' : modelMode === 'autonomous' ? 'Autonomous' : 'Manual'}</span>
      </span>
    </div>
  );
};
