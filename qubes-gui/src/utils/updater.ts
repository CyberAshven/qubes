import { check } from '@tauri-apps/plugin-updater';
import { relaunch } from '@tauri-apps/plugin-process';
import { getVersion } from '@tauri-apps/api/app';

export interface UpdateStatus {
  available: boolean;
  currentVersion: string;
  newVersion?: string;
  error?: string;
}

export interface UpdateProgress {
  downloaded: number;
  total: number;
}

/**
 * Get the current app version
 */
async function getCurrentVersion(): Promise<string> {
  try {
    return await getVersion();
  } catch {
    return '0.1.0'; // Fallback
  }
}

/**
 * Check if an update is available
 */
export async function checkForUpdate(): Promise<UpdateStatus> {
  const currentVersion = await getCurrentVersion();

  try {
    const update = await check();

    if (update) {
      return {
        available: true,
        currentVersion: update.currentVersion,
        newVersion: update.version,
      };
    }

    return {
      available: false,
      currentVersion,
    };
  } catch (error) {
    console.error('Failed to check for updates:', error);

    // Before first release, any error means "no updates available"
    // This is cleaner than showing confusing error messages
    // Real network errors will be obvious (app won't work at all)
    return {
      available: false,
      currentVersion,
      // Don't show error - just treat as "no updates"
    };
  }
}

/**
 * Download and install an update
 * @param onProgress - Callback for download progress
 */
export async function downloadAndInstallUpdate(
  onProgress?: (progress: UpdateProgress) => void
): Promise<boolean> {
  try {
    const update = await check();

    if (!update) {
      console.log('No update available');
      return false;
    }

    console.log(`Downloading update ${update.version}...`);

    // Download the update with progress tracking
    await update.downloadAndInstall((event) => {
      switch (event.event) {
        case 'Started':
          console.log(`Download started, total size: ${event.data.contentLength} bytes`);
          break;
        case 'Progress':
          if (onProgress && event.data.contentLength) {
            onProgress({
              downloaded: event.data.chunkLength,
              total: event.data.contentLength,
            });
          }
          break;
        case 'Finished':
          console.log('Download finished');
          break;
      }
    });

    console.log('Update installed, relaunching...');
    await relaunch();

    return true;
  } catch (error) {
    console.error('Failed to download/install update:', error);
    throw error;
  }
}

/**
 * Check for updates silently on app startup
 * Returns update status (always includes currentVersion)
 */
export async function checkForUpdateSilently(): Promise<UpdateStatus | null> {
  try {
    const status = await checkForUpdate();

    if (status.available) {
      console.log(`Update available: ${status.newVersion}`);
    }

    // Always return status so we have currentVersion
    return status;
  } catch (error) {
    // Silently fail on startup check
    console.warn('Silent update check failed:', error);
    return null;
  }
}
