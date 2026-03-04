/**
 * WalletConnect Button
 *
 * Shows "Connect Wallet" when disconnected, truncated address when connected.
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

  if (connecting) {
    return (
      <button className={`wallet-connect-btn connecting ${className}`} disabled>
        Connecting...
      </button>
    );
  }

  if (connected && address) {
    return (
      <div className={`wallet-connected ${className}`}>
        <span className="wallet-address" title={address}>
          {compact ? truncateAddress(address) : address}
        </span>
        <button
          className="wallet-disconnect-btn"
          onClick={disconnect}
          title="Disconnect wallet"
        >
          x
        </button>
        {error && <span className="wallet-error">{error}</span>}
      </div>
    );
  }

  return (
    <div className={className}>
      <button className="wallet-connect-btn" onClick={connect}>
        Connect Wallet
      </button>
      {error && <span className="wallet-error">{error}</span>}
    </div>
  );
}
