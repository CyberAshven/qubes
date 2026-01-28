import { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';

interface ManagedServerStatus {
  state: 'stopped' | 'starting' | 'loading_model' | 'warming_up' | 'ready' | 'error';
  message: string;
  progress: number;
  error: string | null;
  model_loaded: boolean;
  optimized: boolean;
  gpu_name: string | null;
  started_at: string | null;
  ready_at: string | null;
  restart_count: number;
}

interface WSL2TTSStatusIndicatorProps {
  /** Show full status text (for settings panel) vs compact (for chat) */
  compact?: boolean;
  /** Only show when not ready (hide when working) */
  showOnlyWhenLoading?: boolean;
  /** Custom class for styling */
  className?: string;
}

export const WSL2TTSStatusIndicator: React.FC<WSL2TTSStatusIndicatorProps> = ({
  compact = false,
  showOnlyWhenLoading = false,
  className = '',
}) => {
  const [status, setStatus] = useState<ManagedServerStatus | null>(null);
  const [isPolling, setIsPolling] = useState(true);

  useEffect(() => {
    let mounted = true;
    let pollInterval: number | null = null;

    const fetchStatus = async () => {
      try {
        const result = await invoke<ManagedServerStatus>('get_wsl2_tts_managed_status');
        if (mounted) {
          setStatus(result);

          // Stop polling once ready or in error state (not recoverable)
          if (result.state === 'ready') {
            setIsPolling(false);
            if (pollInterval) {
              clearInterval(pollInterval);
              pollInterval = null;
            }
          }
        }
      } catch (err) {
        console.error('Failed to get WSL2 TTS status:', err);
        // Don't stop polling on error - server might not be available yet
      }
    };

    // Initial fetch
    fetchStatus();

    // Poll every 2 seconds while loading
    if (isPolling) {
      pollInterval = window.setInterval(fetchStatus, 2000);
    }

    return () => {
      mounted = false;
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [isPolling]);

  // Don't render if we want to hide when ready
  if (showOnlyWhenLoading && (!status || status.state === 'ready' || status.state === 'stopped')) {
    return null;
  }

  // Don't render if no status yet
  if (!status) {
    return null;
  }

  const getStateIcon = () => {
    switch (status.state) {
      case 'stopped':
        return '⏸';
      case 'starting':
      case 'loading_model':
      case 'warming_up':
        return '⏳';
      case 'ready':
        return '✓';
      case 'error':
        return '⚠';
      default:
        return '•';
    }
  };

  const getStateColor = () => {
    switch (status.state) {
      case 'stopped':
        return 'text-gray-400';
      case 'starting':
      case 'loading_model':
      case 'warming_up':
        return 'text-yellow-400';
      case 'ready':
        return 'text-green-400';
      case 'error':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  };

  const getStateText = () => {
    switch (status.state) {
      case 'stopped':
        return 'TTS Stopped';
      case 'starting':
        return 'Starting TTS...';
      case 'loading_model':
        return 'Loading TTS Model...';
      case 'warming_up':
        return 'Warming Up TTS...';
      case 'ready':
        return 'TTS Ready';
      case 'error':
        return 'TTS Error';
      default:
        return 'TTS';
    }
  };

  if (compact) {
    // Compact mode: just icon and short text
    return (
      <div className={`flex items-center gap-1 text-xs ${getStateColor()} ${className}`}>
        <span className={status.state === 'warming_up' || status.state === 'loading_model' ? 'animate-pulse' : ''}>
          {getStateIcon()}
        </span>
        <span>{getStateText()}</span>
        {status.progress > 0 && status.progress < 100 && (
          <span className="text-gray-500">({status.progress}%)</span>
        )}
      </div>
    );
  }

  // Full mode: more details
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <div className={`flex items-center gap-2 ${getStateColor()}`}>
        <span className={`text-lg ${status.state === 'warming_up' || status.state === 'loading_model' ? 'animate-pulse' : ''}`}>
          {getStateIcon()}
        </span>
        <span className="font-medium">{getStateText()}</span>
      </div>

      {status.message && (
        <p className="text-sm text-gray-400">{status.message}</p>
      )}

      {status.progress > 0 && status.progress < 100 && (
        <div className="w-full bg-gray-700 rounded-full h-1.5">
          <div
            className="bg-yellow-400 h-1.5 rounded-full transition-all duration-300"
            style={{ width: `${status.progress}%` }}
          />
        </div>
      )}

      {status.error && (
        <p className="text-sm text-red-400">{status.error}</p>
      )}

      {status.state === 'ready' && status.gpu_name && (
        <p className="text-xs text-gray-500">
          GPU: {status.gpu_name}
          {status.optimized && ' (Triton optimized)'}
        </p>
      )}
    </div>
  );
};
