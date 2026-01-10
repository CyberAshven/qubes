import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { GlassCard, GlassButton } from '../glass';

interface Qube {
  qube_id: string;
  name: string;
  wallet_address?: string;  // P2SH address (p) - for sending BCH
  recipient_address?: string;  // NFT address (z) - owner's token address
  wallet_owner_q_address?: string;  // Owner's BCH address (q) - for private key
}

interface WalletSecurityModalProps {
  isOpen: boolean;
  qube: Qube;
  qubes: Qube[];
  walletSecurity: {
    addresses_with_keys: string[];
    whitelists: Record<string, string[]>;
  };
  userId: string;
  password: string;
  onClose: () => void;
  onSave: () => void;
}

export const WalletSecurityModal: React.FC<WalletSecurityModalProps> = ({
  isOpen,
  qube,
  qubes,
  walletSecurity,
  userId,
  password,
  onClose,
  onSave,
}) => {
  const [wifInput, setWifInput] = useState('');
  const [showWif, setShowWif] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [localWhitelist, setLocalWhitelist] = useState<string[]>([]);

  // NFT address (z) is used for key storage internally
  const nftAddress = qube.recipient_address || '';
  const hasStoredKey = walletSecurity.addresses_with_keys.includes(nftAddress);
  // BCH address (q) is shown to user - this is the address for their private key
  const bchAddress = qube.wallet_owner_q_address || '';

  // Initialize local whitelist from props
  useEffect(() => {
    setLocalWhitelist(walletSecurity.whitelists[qube.qube_id] || []);
  }, [walletSecurity.whitelists, qube.qube_id]);

  // Other qubes that can be whitelisted (have P2SH wallets)
  const otherQubes = qubes.filter(
    (q) => q.qube_id !== qube.qube_id && q.wallet_address
  );

  const handleSaveKey = async () => {
    if (!wifInput.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const result = await invoke<{ success: boolean; error?: string }>(
        'save_owner_key',
        {
          userId,
          nftAddress,
          ownerWif: wifInput,
          password,
        }
      );
      if (result.success) {
        setWifInput('');
        onSave();
      } else {
        setError(result.error || 'Failed to save key');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save key');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteKey = async () => {
    setDeleting(true);
    setError(null);
    try {
      await invoke('delete_owner_key', { userId, nftAddress, password });
      onSave();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete key');
    } finally {
      setDeleting(false);
    }
  };

  const handleWhitelistToggle = async (
    targetAddress: string,
    enabled: boolean
  ) => {
    const newWhitelist = enabled
      ? [...localWhitelist, targetAddress]
      : localWhitelist.filter((a) => a !== targetAddress);

    // Update local state immediately for responsive UI
    setLocalWhitelist(newWhitelist);

    try {
      await invoke('update_whitelist', {
        userId,
        qubeId: qube.qube_id,
        whitelist: newWhitelist,
        password,
      });
      onSave();
    } catch (e) {
      // Revert on error
      setLocalWhitelist(localWhitelist);
      setError(e instanceof Error ? e.message : 'Failed to update whitelist');
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <GlassCard
        className="w-full max-w-md p-6 m-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-display text-accent-primary mb-1 flex items-center gap-2">
          <span>🔐</span> Wallet Security
        </h2>
        <p className="text-sm text-text-secondary mb-4">{qube.name}</p>

        {error && (
          <div className="bg-red-500/20 text-red-400 text-sm p-3 rounded-lg mb-4">
            {error}
          </div>
        )}

        {/* Owner Key Section */}
        <div className="mb-5">
          <label className="text-xs text-text-tertiary mb-2 block uppercase tracking-wide">
            Owner Private Key
          </label>
          <p className="text-[10px] text-text-tertiary mb-2 break-all">
            Bitcoin Cash (BCH) Address: {bchAddress}
          </p>
          {hasStoredKey ? (
            <div className="flex items-center gap-3 p-3 bg-glass-bg/30 rounded-lg border border-glass-border">
              <span className="flex-1 text-sm text-accent-success flex items-center gap-2">
                <span className="text-lg">✓</span>
                Key stored for this address
              </span>
              <GlassButton
                onClick={handleDeleteKey}
                disabled={deleting}
                variant="secondary"
                className="text-red-400 hover:text-red-300"
              >
                {deleting ? '...' : 'Delete'}
              </GlassButton>
            </div>
          ) : (
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <input
                  type={showWif ? 'text' : 'password'}
                  value={wifInput}
                  onChange={(e) => setWifInput(e.target.value)}
                  placeholder="Enter WIF private key..."
                  className="w-full px-3 py-2 bg-glass-bg backdrop-blur-glass border border-glass-border rounded-lg text-text-primary text-sm font-mono placeholder-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-primary/50 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowWif(!showWif)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-tertiary hover:text-text-primary text-sm"
                >
                  {showWif ? '🙈' : '👁'}
                </button>
              </div>
              <GlassButton
                onClick={handleSaveKey}
                disabled={!wifInput || saving}
                variant="primary"
              >
                {saving ? '...' : 'Save'}
              </GlassButton>
            </div>
          )}
        </div>

        {/* Whitelist Section */}
        <div className="border-t border-glass-border pt-4">
          <label className="text-xs text-text-tertiary mb-2 block uppercase tracking-wide">
            Auto-Send Whitelist
          </label>
          <p className="text-[10px] text-text-tertiary mb-3">
            {qube.name} can send BCH to these Qubes without your approval:
          </p>

          {!hasStoredKey ? (
            <p className="text-xs text-accent-warning bg-accent-warning/10 p-3 rounded-lg">
              Store owner key first to enable auto-send whitelist.
            </p>
          ) : otherQubes.length === 0 ? (
            <p className="text-xs text-text-tertiary">
              No other Qubes with wallets to whitelist.
            </p>
          ) : (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {otherQubes.map((otherQube) => (
                <label
                  key={otherQube.qube_id}
                  className="flex items-start gap-3 p-2 rounded-lg hover:bg-glass-bg/30 cursor-pointer transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={localWhitelist.includes(
                      otherQube.wallet_address!
                    )}
                    onChange={(e) =>
                      handleWhitelistToggle(
                        otherQube.wallet_address!,
                        e.target.checked
                      )
                    }
                    className="w-4 h-4 mt-0.5 rounded border-glass-border bg-glass-bg text-accent-primary focus:ring-accent-primary/50"
                  />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm text-text-primary block">
                      {otherQube.name}
                    </span>
                    <span className="text-[10px] text-text-tertiary break-all">
                      {otherQube.wallet_address}
                    </span>
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Close Button */}
        <div className="mt-5 flex justify-end">
          <GlassButton onClick={onClose} variant="secondary">
            Close
          </GlassButton>
        </div>
      </GlassCard>
    </div>
  );
};
