/**
 * WalletConnect Button
 *
 * Shows "Connect Wallet" when disconnected.
 * When connecting, shows a QR code + copyable URI for BCH wallets.
 * When connected, shows truncated address + disconnect.
 */

import React, { useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { useWallet } from '../contexts/WalletContext';

interface Props {
  className?: string;
  compact?: boolean;
}

export default function WalletConnectButton({ className = '', compact = false }: Props) {
  const { connected, address, connecting, wcUri, error, connect, disconnect } = useWallet();
  const [copied, setCopied] = useState(false);

  const truncateAddress = (addr: string) => {
    if (addr.length <= 20) return addr;
    const prefix = addr.includes(':') ? addr.split(':')[0] + ':' : '';
    const hash = addr.includes(':') ? addr.split(':')[1] : addr;
    return `${prefix}${hash.slice(0, 6)}...${hash.slice(-4)}`;
  };

  const handleCopyUri = async () => {
    if (!wcUri) return;
    try {
      await navigator.clipboard.writeText(wcUri);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback: select the text
    }
  };

  // Connected state
  if (connected && address) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <span
          className="px-3 py-1.5 rounded-lg bg-accent-primary/10 border border-accent-primary/30 text-accent-primary text-sm font-mono"
          title={address}
        >
          {truncateAddress(address)}
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

  // Connecting state — show QR code + copy URI
  if (connecting && wcUri) {
    return (
      <div className={`${className}`}>
        <div className="p-4 bg-white rounded-lg inline-block">
          <QRCodeSVG value={wcUri} size={200} />
        </div>
        <p className="text-xs text-text-secondary mt-3 mb-2">
          Scan with your BCH wallet, or copy the URI below:
        </p>
        <div className="flex items-center gap-2">
          <input
            type="text"
            readOnly
            value={wcUri}
            className="flex-1 px-3 py-1.5 bg-glass-bg border border-glass-border rounded-lg text-text-tertiary text-xs font-mono truncate"
            onClick={(e) => (e.target as HTMLInputElement).select()}
          />
          <button
            onClick={handleCopyUri}
            className="px-3 py-1.5 rounded-lg bg-accent-primary/20 border border-accent-primary/40 text-accent-primary text-xs font-medium hover:bg-accent-primary/30 transition-colors whitespace-nowrap"
          >
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
        <p className="text-xs text-text-tertiary mt-2">
          Waiting for wallet to connect...
        </p>
      </div>
    );
  }

  // Connecting but no URI yet
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

  // Disconnected state
  return (
    <div className={className}>
      <button
        className="px-4 py-2 rounded-lg bg-accent-primary/20 border border-accent-primary/40 text-accent-primary text-sm font-medium hover:bg-accent-primary/30 transition-colors"
        onClick={connect}
      >
        Connect Wallet
      </button>
      {error && (
        <p className="text-xs text-accent-danger mt-2">{error}</p>
      )}
    </div>
  );
}
