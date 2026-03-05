/**
 * WalletConnect Button
 *
 * Shows "Connect Wallet" when disconnected, truncated address when connected.
 * Displays user-friendly error messages for configuration issues.
 */

import React from 'react';
import { useWallet } from '../contexts/WalletContext';

interface Props {
  className?: string;
  compact?: boolean;
}

export default function WalletConnectButton({ className = '', compact = false }: Props) {
  const { connected, address, connecting, error, connect, disconnect } = useWallet();

  const truncateAddress = (addr: string) => {
    if (addr.length <= 20) return addr;
    // "bitcoincash:qz1234...5678"
    const prefix = addr.includes(':') ? addr.split(':')[0] + ':' : '';
    const hash = addr.includes(':') ? addr.split(':')[1] : addr;
    return `${prefix}${hash.slice(0, 6)}...${hash.slice(-4)}`;
  };

  // Make error messages user-friendly
  const friendlyError = (msg: string) => {
    if (msg.includes('VITE_WC_PROJECT_ID')) {
      return 'WalletConnect not configured. A project ID is required — register free at cloud.reown.com';
    }
    return msg;
  };

  if (connecting) {
    return (
      <button
        className={`px-4 py-2 rounded-lg bg-glass-bg border border-glass-border text-text-tertiary text-sm cursor-wait ${className}`}
        disabled
      >
        Connecting...
      </button>
    );
  }

  if (connected && address) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <span
          className="px-3 py-1.5 rounded-lg bg-accent-primary/10 border border-accent-primary/30 text-accent-primary text-sm font-mono"
          title={address}
        >
          {compact ? truncateAddress(address) : truncateAddress(address)}
        </span>
        <button
          className="px-2 py-1.5 rounded-lg bg-glass-bg border border-glass-border text-text-tertiary hover:text-accent-danger text-xs transition-colors"
          onClick={disconnect}
          title="Disconnect wallet"
        >
          Disconnect
        </button>
      </div>
    );
  }

  return (
    <div className={className}>
      <button
        className="px-4 py-2 rounded-lg bg-accent-primary/20 border border-accent-primary/40 text-accent-primary text-sm font-medium hover:bg-accent-primary/30 transition-colors"
        onClick={connect}
      >
        Connect Wallet
      </button>
      {error && (
        <p className="text-xs text-accent-danger mt-2">
          {friendlyError(error)}
        </p>
      )}
    </div>
  );
}
