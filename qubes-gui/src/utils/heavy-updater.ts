import { invoke } from '@tauri-apps/api/core';
import { listen, type UnlistenFn } from '@tauri-apps/api/event';
import { relaunch } from '@tauri-apps/plugin-process';
import type { UpdateStatus, UpdateProgress } from './updater';

export interface HeavyUpdateInfo {
  available: boolean;
  current_version: string;
  new_version: string | null;
  url: string | null;
  sha256: string | null;
  size: number | null;
  notes: string | null;
}

/**
 * Check if this installation is a heavy bundle (ZIP extract with qubes-backend/ subfolder)
 */
export async function isHeavyBundle(): Promise<boolean> {
  try {
    return await invoke<boolean>('is_heavy_bundle');
  } catch {
    return false;
  }
}

/**
 * Get the current backend version from the VERSION file
 */
export async function getBackendVersion(): Promise<string> {
  try {
    return await invoke<string>('get_backend_version');
  } catch {
    return '0.0.0';
  }
}

/**
 * Check for heavy bundle updates. Returns UpdateStatus matching the light updater API.
 */
export async function checkHeavyUpdate(): Promise<UpdateStatus> {
  try {
    const info = await invoke<HeavyUpdateInfo>('check_heavy_update');

    return {
      available: info.available,
      currentVersion: info.current_version,
      newVersion: info.new_version ?? undefined,
      // Expose size info via the error field (hacky but avoids breaking the interface)
      // The hook will parse this separately
    };
  } catch (error) {
    console.error('Failed to check for heavy update:', error);
    return {
      available: false,
      currentVersion: await getBackendVersion(),
    };
  }
}

/**
 * Get full heavy update info (includes URL, SHA-256, size)
 */
export async function getHeavyUpdateInfo(): Promise<HeavyUpdateInfo | null> {
  try {
    const info = await invoke<HeavyUpdateInfo>('check_heavy_update');
    return info.available ? info : null;
  } catch {
    return null;
  }
}

/**
 * Download and install a heavy bundle update with progress tracking.
 * Handles: download → verify → install → prompt restart.
 */
export async function downloadAndInstallHeavyUpdate(
  onProgress?: (progress: UpdateProgress) => void,
  onStatusChange?: (status: 'downloading' | 'verifying' | 'installing' | 'restarting') => void,
): Promise<boolean> {
  let unlisten: UnlistenFn | null = null;

  try {
    // Get update info
    const info = await invoke<HeavyUpdateInfo>('check_heavy_update');
    if (!info.available || !info.url || !info.sha256) {
      return false;
    }

    // Listen for download progress events
    if (onProgress) {
      unlisten = await listen<{ downloaded: number; total: number }>(
        'heavy-update-progress',
        (event) => {
          onProgress({
            downloaded: event.payload.downloaded,
            total: event.payload.total,
          });
        },
      );
    }

    // Download
    onStatusChange?.('downloading');
    const archivePath = await invoke<string>('download_heavy_update', {
      url: info.url,
    });

    // Verify
    onStatusChange?.('verifying');
    const valid = await invoke<boolean>('verify_heavy_update', {
      path: archivePath,
      expectedSha256: info.sha256,
    });

    if (!valid) {
      throw new Error('Update verification failed: SHA-256 mismatch. The download may be corrupted.');
    }

    // Install (atomic swap)
    onStatusChange?.('installing');
    await invoke<boolean>('install_heavy_update', {
      archivePath,
    });

    // Restart
    onStatusChange?.('restarting');
    await relaunch();

    return true;
  } catch (error) {
    console.error('Heavy update failed:', error);
    throw error;
  } finally {
    if (unlisten) {
      unlisten();
    }
  }
}

/**
 * Clean up leftover .old files from a previous update
 */
export async function cleanupOldBackend(): Promise<void> {
  try {
    await invoke('cleanup_old_backend');
  } catch {
    // Non-critical, ignore errors
  }
}

/**
 * Format bytes into human-readable size
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(i > 1 ? 1 : 0)} ${units[i]}`;
}
