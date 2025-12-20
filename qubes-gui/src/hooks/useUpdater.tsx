import { useState, useCallback, useEffect } from 'react';
import {
  checkForUpdate,
  downloadAndInstallUpdate,
  checkForUpdateSilently,
  UpdateStatus,
  UpdateProgress,
} from '../utils/updater';

interface UseUpdaterReturn {
  // State
  updateAvailable: boolean;
  updateStatus: UpdateStatus | null;
  isChecking: boolean;
  isDownloading: boolean;
  downloadProgress: UpdateProgress | null;
  error: string | null;

  // Actions
  checkForUpdates: () => Promise<void>;
  installUpdate: () => Promise<void>;
  dismissUpdate: () => void;
}

export function useUpdater(checkOnMount: boolean = false): UseUpdaterReturn {
  const [updateStatus, setUpdateStatus] = useState<UpdateStatus | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState<UpdateProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState(false);

  // Check for updates
  const checkForUpdates = useCallback(async () => {
    setIsChecking(true);
    setError(null);

    try {
      const status = await checkForUpdate();
      setUpdateStatus(status);
      setDismissed(false);

      if (status.error) {
        setError(status.error);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to check for updates');
    } finally {
      setIsChecking(false);
    }
  }, []);

  // Download and install update
  const installUpdate = useCallback(async () => {
    if (!updateStatus?.available) return;

    setIsDownloading(true);
    setError(null);

    try {
      await downloadAndInstallUpdate((progress) => {
        setDownloadProgress(progress);
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to install update');
      setIsDownloading(false);
    }
    // Note: If successful, app will relaunch, so we won't reach here
  }, [updateStatus]);

  // Dismiss update notification
  const dismissUpdate = useCallback(() => {
    setDismissed(true);
  }, []);

  // Check on mount if requested
  useEffect(() => {
    if (checkOnMount) {
      checkForUpdateSilently().then((status) => {
        if (status) {
          setUpdateStatus(status);
        }
      });
    }
  }, [checkOnMount]);

  return {
    updateAvailable: updateStatus?.available === true && !dismissed,
    updateStatus,
    isChecking,
    isDownloading,
    downloadProgress,
    error,
    checkForUpdates,
    installUpdate,
    dismissUpdate,
  };
}
