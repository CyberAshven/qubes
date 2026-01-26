import { useState, useEffect, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { GlassCard, GlassButton } from '../glass';
import { useAuth } from '../../hooks/useAuth';

interface WSL2TTSStatus {
  success: boolean;
  error?: string;
  wsl2_installed: boolean;
  ubuntu_installed: boolean;
  ubuntu_distro?: string;
  setup_complete: boolean;
  venv_exists: boolean;
  pytorch_installed: boolean;
  qwen_tts_installed: boolean;
  model_downloaded: boolean;
  server_running: boolean;
  server_ready: boolean;
  gpu_detected: boolean;
  gpu_name?: string;
  cuda_version?: string;
}

interface SetupProgress {
  success: boolean;
  stage: string;
  stage_name: string;
  percentage: number;
  message: string;
  error?: string;
  started_at?: string;
  completed_at?: string;
}

export const LocalTTSSetupPanel: React.FC = () => {
  const { userId } = useAuth();

  // Status state
  const [status, setStatus] = useState<WSL2TTSStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Setup state
  const [isSettingUp, setIsSettingUp] = useState(false);
  const [setupProgress, setSetupProgress] = useState<SetupProgress | null>(null);

  // Server control state
  const [startingServer, setStartingServer] = useState(false);
  const [stoppingServer, setStoppingServer] = useState(false);

  // Uninstall state
  const [uninstalling, setUninstalling] = useState(false);
  const [showUninstallConfirm, setShowUninstallConfirm] = useState(false);

  // Collapsed state - default to collapsed
  const [isExpanded, setIsExpanded] = useState(false);

  // Load status on mount and periodically
  useEffect(() => {
    loadStatus();
  }, [userId]);

  // Poll for setup progress when setting up
  useEffect(() => {
    if (!isSettingUp) return;

    const interval = setInterval(async () => {
      try {
        const progress = await invoke<SetupProgress>('get_wsl2_tts_setup_progress', {
          userId,
        });

        setSetupProgress(progress);

        // Check if setup completed or failed
        if (progress.stage === 'complete' || progress.error) {
          setIsSettingUp(false);
          loadStatus(); // Refresh status
        }
      } catch (err) {
        console.error('Failed to get setup progress:', err);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [isSettingUp, userId]);

  const loadStatus = async () => {
    if (!userId) return;

    setLoadingStatus(true);
    setError(null);

    try {
      const result = await invoke<WSL2TTSStatus>('check_wsl2_tts_status', {
        userId,
      });

      setStatus(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to check status');
    } finally {
      setLoadingStatus(false);
    }
  };

  const handleSetup = async () => {
    setIsSettingUp(true);
    setSetupProgress({
      success: true,
      stage: 'starting',
      stage_name: 'Starting setup...',
      percentage: 0,
      message: 'Initializing...',
    });
    setError(null);

    try {
      const result = await invoke<{ success: boolean; error?: string }>('setup_wsl2_tts', {
        userId,
      });

      if (!result.success) {
        setError(result.error || 'Setup failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Setup failed');
    } finally {
      setIsSettingUp(false);
      loadStatus();
    }
  };

  const handleStartServer = async () => {
    setStartingServer(true);
    setError(null);

    try {
      const result = await invoke<{ success: boolean; error?: string; message?: string }>('start_wsl2_tts_server', {
        userId,
      });

      if (!result.success) {
        setError(result.error || 'Failed to start server');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start server');
    } finally {
      setStartingServer(false);
      loadStatus();
    }
  };

  const handleStopServer = async () => {
    setStoppingServer(true);
    setError(null);

    try {
      const result = await invoke<{ success: boolean; error?: string }>('stop_wsl2_tts_server', {
        userId,
      });

      if (!result.success) {
        setError(result.error || 'Failed to stop server');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop server');
    } finally {
      setStoppingServer(false);
      loadStatus();
    }
  };

  const handleUninstall = async () => {
    setUninstalling(true);
    setShowUninstallConfirm(false);
    setError(null);

    try {
      const result = await invoke<{ success: boolean; error?: string }>('uninstall_wsl2_tts', {
        userId,
      });

      if (!result.success) {
        setError(result.error || 'Failed to uninstall');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to uninstall');
    } finally {
      setUninstalling(false);
      loadStatus();
    }
  };

  // Render status badges
  const StatusBadge = ({ ok, label }: { ok: boolean; label: string }) => (
    <div className={`flex items-center gap-1.5 px-2 py-1 rounded text-[10px] ${
      ok ? 'bg-green-500/10 text-green-400' : 'bg-white/5 text-text-tertiary'
    }`}>
      <span>{ok ? '✓' : '○'}</span>
      <span>{label}</span>
    </div>
  );

  if (loadingStatus) {
    return (
      <div className="text-center text-text-tertiary text-sm py-4">
        Checking local TTS status...
      </div>
    );
  }

  // Determine compact status text
  const getStatusSummary = () => {
    if (!status) return 'Loading...';
    if (!status.wsl2_installed || !status.ubuntu_installed) return 'Setup Required';
    if (!status.setup_complete) return 'Ready to Install';
    if (status.server_ready) return 'Running';
    if (status.server_running) return 'Starting...';
    return 'Stopped';
  };

  const statusColor = () => {
    if (!status) return 'text-text-tertiary';
    if (status.server_ready) return 'text-green-400';
    if (status.server_running) return 'text-yellow-400';
    if (status.setup_complete) return 'text-text-secondary';
    return 'text-yellow-400';
  };

  return (
    <div className="space-y-3">
      {/* Collapsible Header */}
      <div
        className="flex items-center justify-between gap-3 cursor-pointer group"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className={`text-xs transition-transform ${isExpanded ? 'rotate-90' : ''}`}>▶</span>
          <h3 className="text-sm font-medium text-text-primary">Local TTS (WSL2)</h3>
          <span className={`text-[10px] ${statusColor()}`}>
            • {getStatusSummary()}
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {status?.server_ready && (
            <span className="text-[9px] bg-green-500/20 text-green-400 px-1.5 py-0.5 rounded">
              Server Running
            </span>
          )}
          <GlassButton
            onClick={(e) => { e.stopPropagation(); loadStatus(); }}
            variant="secondary"
            size="sm"
            className="text-[10px] h-6 px-2 whitespace-nowrap flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
          >
            ↻
          </GlassButton>
        </div>
      </div>

      {/* Error display - always visible */}
      {error && (
        <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-400">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">Dismiss</button>
        </div>
      )}

      {/* Expanded content */}
      {isExpanded && (
        <div className="space-y-3 pl-4 border-l border-white/10">

      {/* Setup Progress */}
      {isSettingUp && setupProgress && (
        <GlassCard className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-text-primary font-medium">
              {setupProgress.stage_name}
            </span>
            <span className="text-xs text-text-tertiary">
              {setupProgress.percentage}%
            </span>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-white/10 rounded-full h-2">
            <div
              className="h-2 rounded-full bg-accent-primary transition-all duration-500"
              style={{ width: `${setupProgress.percentage}%` }}
            />
          </div>

          {setupProgress.message && (
            <p className="text-[10px] text-text-tertiary">
              {setupProgress.message}
            </p>
          )}

          {setupProgress.error && (
            <p className="text-[10px] text-red-400">
              Error: {setupProgress.error}
            </p>
          )}
        </GlassCard>
      )}

      {/* Main status section */}
      {status && !isSettingUp && (
        <>
          {/* Prerequisites check */}
          {!status.wsl2_installed || !status.ubuntu_installed ? (
            <GlassCard className="p-4 space-y-3">
              <div className="flex items-center gap-2 text-yellow-400">
                <span>⚠️</span>
                <span className="text-sm font-medium">Prerequisites Required</span>
              </div>

              <div className="space-y-2 text-xs text-text-secondary">
                {!status.wsl2_installed && (
                  <div className="flex items-center gap-2">
                    <span className="text-red-400">✗</span>
                    <span>WSL2 not installed</span>
                  </div>
                )}
                {status.wsl2_installed && !status.ubuntu_installed && (
                  <div className="flex items-center gap-2">
                    <span className="text-red-400">✗</span>
                    <span>Ubuntu not installed in WSL2</span>
                  </div>
                )}
              </div>

              <div className="pt-2 border-t border-white/10 space-y-2 text-[10px] text-text-tertiary">
                <p className="font-medium text-text-secondary">To install WSL2 with Ubuntu:</p>
                <ol className="list-decimal list-inside space-y-1">
                  <li>Open PowerShell as Administrator</li>
                  <li>Run: <code className="bg-white/10 px-1 rounded">wsl --install -d Ubuntu-22.04</code></li>
                  <li>Restart your computer when prompted</li>
                  <li>After restart, Ubuntu will finish installing (create a username/password)</li>
                  <li>Come back here and click Refresh</li>
                </ol>
              </div>
            </GlassCard>
          ) : !status.setup_complete ? (
            /* Setup needed */
            <GlassCard className="p-4 space-y-3">
              <div className="flex items-center gap-2 text-accent-primary">
                <span>🚀</span>
                <span className="text-sm font-medium">Ready to Set Up</span>
              </div>

              <div className="flex flex-wrap gap-2">
                <StatusBadge ok={status.wsl2_installed} label="WSL2" />
                <StatusBadge ok={status.ubuntu_installed} label="Ubuntu" />
                <StatusBadge ok={status.venv_exists} label="Python venv" />
                <StatusBadge ok={status.pytorch_installed} label="PyTorch" />
                <StatusBadge ok={status.qwen_tts_installed} label="qwen-tts" />
                <StatusBadge ok={status.model_downloaded} label="Model" />
              </div>

              <p className="text-[10px] text-text-tertiary">
                This will set up Qwen3-TTS in WSL2 for high-quality local voice synthesis.
                The setup downloads about 4GB of model files and may take 10-20 minutes.
              </p>

              <GlassButton
                onClick={handleSetup}
                disabled={isSettingUp}
                className="w-full"
              >
                {isSettingUp ? 'Setting up...' : 'Set Up Local TTS'}
              </GlassButton>
            </GlassCard>
          ) : (
            /* Setup complete - show server controls */
            <GlassCard className="p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-green-400">
                  <span>✓</span>
                  <span className="text-sm font-medium">Local TTS Ready</span>
                </div>
                {status.server_ready && (
                  <span className="text-[10px] bg-green-500/20 text-green-400 px-2 py-0.5 rounded">
                    Server Running
                  </span>
                )}
                {status.server_running && !status.server_ready && (
                  <span className="text-[10px] bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded animate-pulse">
                    Loading Model...
                  </span>
                )}
              </div>

              {/* GPU Info */}
              {status.gpu_detected && (
                <div className="text-[10px] text-text-tertiary bg-white/5 rounded p-2">
                  <span className="text-text-secondary">GPU:</span> {status.gpu_name}
                  {status.cuda_version && <span className="ml-2">• CUDA {status.cuda_version}</span>}
                </div>
              )}

              {/* Status indicators */}
              <div className="flex flex-wrap gap-2">
                <StatusBadge ok={status.pytorch_installed} label="PyTorch" />
                <StatusBadge ok={status.qwen_tts_installed} label="qwen-tts" />
                <StatusBadge ok={status.model_downloaded} label="Model" />
                <StatusBadge ok={status.gpu_detected} label="GPU" />
                <StatusBadge ok={status.server_ready} label="Server" />
              </div>

              {/* Server controls */}
              <div className="flex gap-2">
                {!status.server_running ? (
                  <GlassButton
                    onClick={handleStartServer}
                    disabled={startingServer}
                    className="flex-1"
                  >
                    {startingServer ? 'Starting...' : 'Start Server'}
                  </GlassButton>
                ) : (
                  <GlassButton
                    onClick={handleStopServer}
                    disabled={stoppingServer}
                    variant="secondary"
                    className="flex-1"
                  >
                    {stoppingServer ? 'Stopping...' : 'Stop Server'}
                  </GlassButton>
                )}
              </div>

              <p className="text-[10px] text-text-tertiary">
                {status.server_ready
                  ? 'The server is running and ready. Qubes with WSL2 TTS voice will use local generation.'
                  : status.server_running
                  ? 'The server is starting up. First-time model loading takes ~2 minutes for JIT compilation.'
                  : 'Start the server to enable local TTS generation. Server keeps the model loaded for fast synthesis.'}
              </p>

              {/* Uninstall option */}
              <div className="pt-3 border-t border-white/10">
                {showUninstallConfirm ? (
                  <div className="space-y-2">
                    <p className="text-[10px] text-text-secondary">
                      This will remove all WSL2 TTS files including the downloaded model (~4GB).
                      Are you sure?
                    </p>
                    <div className="flex gap-2">
                      <GlassButton
                        onClick={handleUninstall}
                        disabled={uninstalling}
                        variant="secondary"
                        size="sm"
                        className="flex-1 text-red-400 border-red-400/30"
                      >
                        {uninstalling ? 'Uninstalling...' : 'Yes, Uninstall'}
                      </GlassButton>
                      <GlassButton
                        onClick={() => setShowUninstallConfirm(false)}
                        variant="secondary"
                        size="sm"
                        className="flex-1"
                      >
                        Cancel
                      </GlassButton>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => setShowUninstallConfirm(true)}
                    className="text-[10px] text-text-tertiary hover:text-red-400 transition-colors"
                  >
                    Uninstall Local TTS
                  </button>
                )}
              </div>
            </GlassCard>
          )}
        </>
      )}

      {/* Help section */}
      <div className="text-[9px] text-text-tertiary">
        <p className="font-medium text-text-secondary mb-1">About Local TTS:</p>
        <ul className="list-disc list-inside space-y-0.5">
          <li>Uses Qwen3-TTS 1.7B model for high-quality voice synthesis</li>
          <li>Runs entirely on your GPU via WSL2 Ubuntu</li>
          <li>No internet required after setup</li>
          <li>Supports 9 preset voices and 10 languages</li>
          <li>Requires ~6GB VRAM and ~10GB disk space</li>
        </ul>
      </div>
        </div>
      )}
    </div>
  );
};

export default LocalTTSSetupPanel;
