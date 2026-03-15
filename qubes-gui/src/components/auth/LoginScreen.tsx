import React, { useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { open as openDialog } from '@tauri-apps/plugin-dialog';
import { GlassCard } from '../glass/GlassCard';
import { GlassInput } from '../glass/GlassInput';
import { GlassButton } from '../glass/GlassButton';

interface LoginScreenProps {
  onLogin: (username: string, password: string) => Promise<void>;
  onCreateAccount: () => void;
  onResetAccount?: (username: string) => void;
  error?: string | null;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLogin, onCreateAccount, onResetAccount, error }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Restore from backup (file) state
  const [showRestoreModal, setShowRestoreModal] = useState(false);
  const [restoreFilePath, setRestoreFilePath] = useState('');
  const [restorePassword, setRestorePassword] = useState('');
  const [restoreMasterPassword, setRestoreMasterPassword] = useState('');
  const [restoreMasterPasswordConfirm, setRestoreMasterPasswordConfirm] = useState('');
  const [isRestoring, setIsRestoring] = useState(false);
  const [restoreError, setRestoreError] = useState<string | null>(null);

  // Restore from IPFS state
  const [showIpfsRestoreModal, setShowIpfsRestoreModal] = useState(false);
  const [ipfsCid, setIpfsCid] = useState('');
  const [ipfsRestorePassword, setIpfsRestorePassword] = useState('');
  const [ipfsRestoreMasterPassword, setIpfsRestoreMasterPassword] = useState('');
  const [ipfsRestoreMasterPasswordConfirm, setIpfsRestoreMasterPasswordConfirm] = useState('');
  const [isIpfsRestoring, setIsIpfsRestoring] = useState(false);
  const [ipfsRestoreError, setIpfsRestoreError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) return;

    setIsLoading(true);
    try {
      await onLogin(username.trim(), password);
    } catch (err) {
      // Error handled by parent
    } finally {
      setIsLoading(false);
    }
  };

  const handleRestorePickFile = async () => {
    const selected = await openDialog({
      title: 'Select Account Backup',
      filters: [{ name: 'Qube Backup', extensions: ['qube-backup'] }],
      multiple: false,
      directory: false,
    });
    if (selected) {
      setRestoreFilePath(selected as string);
    }
  };

  const handleRestore = async () => {
    if (!restoreFilePath || !restorePassword || !restoreMasterPassword) return;

    if (restoreMasterPassword !== restoreMasterPasswordConfirm) {
      setRestoreError('Master passwords do not match.');
      return;
    }

    if (restoreMasterPassword.length < 8) {
      setRestoreError('Master password must be at least 8 characters.');
      return;
    }

    setIsRestoring(true);
    setRestoreError(null);

    try {
      const result = await invoke<{
        success: boolean;
        imported_count?: number;
        skipped_count?: number;
        user_id?: string;
        error?: string;
      }>('import_account_backup', {
        userId: '_restore',
        importPath: restoreFilePath,
        importPassword: restorePassword,
        masterPassword: restoreMasterPassword,
      });

      if (result.success) {
        alert(`Account restored successfully!\n\n${result.imported_count} Qube(s) imported, ${result.skipped_count} skipped.\n\nPlease sign in with your master password.`);
        setShowRestoreModal(false);
        setRestoreFilePath('');
        setRestorePassword('');
        setRestoreMasterPassword('');
        setRestoreMasterPasswordConfirm('');
        // Pre-fill username if available
        if (result.user_id) {
          setUsername(result.user_id);
          setPassword(restoreMasterPassword);
        }
      } else {
        setRestoreError(result.error || 'Restore failed');
      }
    } catch (err) {
      setRestoreError(`${err}`);
    } finally {
      setIsRestoring(false);
    }
  };

  const handleIpfsRestore = async () => {
    if (!ipfsCid.trim() || !ipfsRestorePassword || !ipfsRestoreMasterPassword) return;

    if (ipfsRestoreMasterPassword !== ipfsRestoreMasterPasswordConfirm) {
      setIpfsRestoreError('Master passwords do not match.');
      return;
    }

    if (ipfsRestoreMasterPassword.length < 8) {
      setIpfsRestoreError('Master password must be at least 8 characters.');
      return;
    }

    setIsIpfsRestoring(true);
    setIpfsRestoreError(null);

    try {
      const result = await invoke<{
        success: boolean;
        imported_count?: number;
        skipped_count?: number;
        user_id?: string;
        error?: string;
      }>('import_account_backup_ipfs', {
        userId: '_restore',
        ipfsCid: ipfsCid.trim(),
        importPassword: ipfsRestorePassword,
        masterPassword: ipfsRestoreMasterPassword,
      });

      if (result.success) {
        alert(`Account restored from IPFS!\n\n${result.imported_count} Qube(s) imported, ${result.skipped_count} skipped.\n\nPlease sign in with your master password.`);
        setShowIpfsRestoreModal(false);
        setIpfsCid('');
        setIpfsRestorePassword('');
        setIpfsRestoreMasterPassword('');
        setIpfsRestoreMasterPasswordConfirm('');
        if (result.user_id) {
          setUsername(result.user_id);
          setPassword(ipfsRestoreMasterPassword);
        }
      } else {
        setIpfsRestoreError(result.error || 'IPFS restore failed');
      }
    } catch (err) {
      setIpfsRestoreError(`${err}`);
    } finally {
      setIsIpfsRestoring(false);
    }
  };

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-bg-primary relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 opacity-30">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-accent-primary/20 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent-secondary/20 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>
      </div>

      {/* Login card */}
      <GlassCard variant="elevated" className="w-full max-w-md p-8 relative z-10">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-display text-accent-primary mb-2">
            QUBES
          </h1>
          <p className="text-text-secondary">
            Sign in to your account
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <GlassInput
            label="Username"
            type="text"
            placeholder="Enter your username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={isLoading}
            autoFocus
          />

          <GlassInput
            label="Master Password"
            type="password"
            placeholder="Enter your master password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isLoading}
          />

          {error && (
            <div className="p-4 bg-accent-danger/10 border border-accent-danger/30 rounded-lg">
              <p className="text-accent-danger text-sm">
                {error.includes('ACCOUNT_CORRUPTED')
                  ? 'This account appears incomplete or corrupted.'
                  : error}
              </p>
              {error.includes('ACCOUNT_CORRUPTED') && onResetAccount && username.trim() && (
                <button
                  onClick={() => onResetAccount(username.trim())}
                  className="mt-3 px-4 py-1.5 rounded bg-accent-danger/20 text-accent-danger hover:bg-accent-danger/30 transition-colors text-xs font-medium"
                >
                  Reset Account &amp; Start Over
                </button>
              )}
            </div>
          )}

          <GlassButton
            type="submit"
            variant="primary"
            size="lg"
            className="w-full"
            disabled={!username.trim() || !password.trim() || isLoading}
            loading={isLoading}
          >
            Sign In
          </GlassButton>
        </form>

        <div className="mt-6 text-center text-text-tertiary text-sm">
          <p>Secured with end-to-end encryption</p>
        </div>

        <div className="mt-4 flex justify-center gap-3 flex-wrap">
          <button
            onClick={onCreateAccount}
            className="text-accent-primary hover:text-accent-primary/80 text-sm font-medium transition-colors"
          >
            Create New Account
          </button>
          <span className="text-text-tertiary">|</span>
          <button
            onClick={() => setShowRestoreModal(true)}
            className="text-accent-secondary hover:text-accent-secondary/80 text-sm font-medium transition-colors"
          >
            Restore from File
          </button>
          <span className="text-text-tertiary">|</span>
          <button
            onClick={() => setShowIpfsRestoreModal(true)}
            className="text-accent-secondary hover:text-accent-secondary/80 text-sm font-medium transition-colors"
          >
            Restore from IPFS
          </button>
        </div>
      </GlassCard>

      {/* Restore from IPFS Modal */}
      {showIpfsRestoreModal && (
        <div className="fixed inset-0 bg-black/95 backdrop-blur-sm flex items-center justify-center z-50">
          <GlassCard variant="elevated" className="w-full max-w-md p-6 mx-4">
            <h2 className="text-xl font-bold text-text-primary mb-2">Restore from IPFS</h2>
            <p className="text-text-secondary text-sm mb-4">
              Restore your account using an IPFS CID from a previous backup.
              The CID was shown when you backed up to IPFS.
            </p>

            <div className="mb-4">
              <label className="block text-text-secondary text-sm mb-1">IPFS CID</label>
              <input
                type="text"
                value={ipfsCid}
                onChange={(e) => setIpfsCid(e.target.value)}
                placeholder="Qm... or bafy..."
                className="w-full bg-surface-secondary border border-border-primary rounded-lg px-3 py-2 text-text-primary text-sm font-mono"
              />
            </div>

            <div className="mb-4">
              <label className="block text-text-secondary text-sm mb-1">Backup Password</label>
              <input
                type="password"
                value={ipfsRestorePassword}
                onChange={(e) => setIpfsRestorePassword(e.target.value)}
                placeholder="Password used when creating the backup"
                className="w-full bg-surface-secondary border border-border-primary rounded-lg px-3 py-2 text-text-primary text-sm"
              />
            </div>

            <div className="mb-4">
              <label className="block text-text-secondary text-sm mb-1">Master Password</label>
              <input
                type="password"
                value={ipfsRestoreMasterPassword}
                onChange={(e) => setIpfsRestoreMasterPassword(e.target.value)}
                placeholder="Master password for this device"
                className="w-full bg-surface-secondary border border-border-primary rounded-lg px-3 py-2 text-text-primary text-sm"
              />
            </div>

            <div className="mb-4">
              <label className="block text-text-secondary text-sm mb-1">Confirm Master Password</label>
              <input
                type="password"
                value={ipfsRestoreMasterPasswordConfirm}
                onChange={(e) => setIpfsRestoreMasterPasswordConfirm(e.target.value)}
                placeholder="Confirm master password"
                className="w-full bg-surface-secondary border border-border-primary rounded-lg px-3 py-2 text-text-primary text-sm"
              />
            </div>

            {ipfsRestoreError && (
              <div className="mb-4 p-3 bg-accent-danger/10 border border-accent-danger/30 rounded-lg">
                <p className="text-accent-danger text-sm">{ipfsRestoreError}</p>
              </div>
            )}

            {isIpfsRestoring && (
              <div className="mb-4 p-3 bg-accent-primary/10 border border-accent-primary/30 rounded-lg">
                <p className="text-accent-primary text-sm">Downloading from IPFS and restoring... this may take a moment.</p>
              </div>
            )}

            <div className="flex gap-3 justify-end">
              <GlassButton
                variant="secondary"
                onClick={() => { setShowIpfsRestoreModal(false); setIpfsRestoreError(null); }}
                disabled={isIpfsRestoring}
              >
                Cancel
              </GlassButton>
              <GlassButton
                variant="primary"
                onClick={handleIpfsRestore}
                disabled={!ipfsCid.trim() || !ipfsRestorePassword || !ipfsRestoreMasterPassword || !ipfsRestoreMasterPasswordConfirm || isIpfsRestoring}
                loading={isIpfsRestoring}
              >
                {isIpfsRestoring ? 'Restoring...' : 'Restore from IPFS'}
              </GlassButton>
            </div>
          </GlassCard>
        </div>
      )}

      {/* Restore from File Modal */}
      {showRestoreModal && (
        <div className="fixed inset-0 bg-black/95 backdrop-blur-sm flex items-center justify-center z-50">
          <GlassCard variant="elevated" className="w-full max-w-md p-6 mx-4">
            <h2 className="text-xl font-bold text-text-primary mb-4">Restore from File</h2>
            <p className="text-text-secondary text-sm mb-4">
              Restore your entire account from a <code>.qube-backup</code> file.
              This will set up your account and import all Qubes from the backup.
            </p>

            {/* File picker */}
            <div className="mb-4">
              <label className="block text-text-secondary text-sm mb-1">Backup File</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={restoreFilePath}
                  readOnly
                  placeholder="No file selected"
                  className="flex-1 bg-surface-secondary border border-border-primary rounded-lg px-3 py-2 text-text-primary text-sm truncate"
                />
                <GlassButton variant="secondary" onClick={handleRestorePickFile}>
                  Browse
                </GlassButton>
              </div>
            </div>

            {/* Backup password */}
            <div className="mb-4">
              <label className="block text-text-secondary text-sm mb-1">Backup Password</label>
              <input
                type="password"
                value={restorePassword}
                onChange={(e) => setRestorePassword(e.target.value)}
                placeholder="Password used when creating the backup"
                className="w-full bg-surface-secondary border border-border-primary rounded-lg px-3 py-2 text-text-primary text-sm"
              />
            </div>

            {/* New master password */}
            <div className="mb-4">
              <label className="block text-text-secondary text-sm mb-1">Master Password</label>
              <input
                type="password"
                value={restoreMasterPassword}
                onChange={(e) => setRestoreMasterPassword(e.target.value)}
                placeholder="Master password for this device"
                className="w-full bg-surface-secondary border border-border-primary rounded-lg px-3 py-2 text-text-primary text-sm"
              />
            </div>

            <div className="mb-4">
              <label className="block text-text-secondary text-sm mb-1">Confirm Master Password</label>
              <input
                type="password"
                value={restoreMasterPasswordConfirm}
                onChange={(e) => setRestoreMasterPasswordConfirm(e.target.value)}
                placeholder="Confirm master password"
                className="w-full bg-surface-secondary border border-border-primary rounded-lg px-3 py-2 text-text-primary text-sm"
              />
            </div>

            {restoreError && (
              <div className="mb-4 p-3 bg-accent-danger/10 border border-accent-danger/30 rounded-lg">
                <p className="text-accent-danger text-sm">{restoreError}</p>
              </div>
            )}

            <div className="flex gap-3 justify-end">
              <GlassButton
                variant="secondary"
                onClick={() => { setShowRestoreModal(false); setRestoreError(null); }}
                disabled={isRestoring}
              >
                Cancel
              </GlassButton>
              <GlassButton
                variant="primary"
                onClick={handleRestore}
                disabled={!restoreFilePath || !restorePassword || !restoreMasterPassword || !restoreMasterPasswordConfirm || isRestoring}
                loading={isRestoring}
              >
                {isRestoring ? 'Restoring...' : 'Restore Account'}
              </GlassButton>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
};
