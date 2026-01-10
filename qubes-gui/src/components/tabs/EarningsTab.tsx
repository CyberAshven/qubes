import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { QRCodeSVG } from 'qrcode.react';
import { Qube } from '../../types';
import { GlassCard, GlassButton } from '../glass';
import { useAuth } from '../../hooks/useAuth';
import { useWalletCache } from '../../hooks/useWalletCache';
import { TransactionHistory } from '../wallet/TransactionHistory';

interface EarningsTabProps {
  qubes: Qube[];
  selectedQubeIds: string[];
  onQubeSelect: (qubeId: string) => void;
}

interface WalletInfo {
  balance_sats: number;  // P2SH wallet balance
  balance_bch: number;
  wallet_address: string;  // P2SH address
  nft_address?: string;  // Owner's 'z' address (NFT address)
  nft_balance_sats?: number;  // NFT address balance
  nft_balance_bch?: number;
  owner_pubkey: string;
  qube_pubkey: string;
  pending_transactions: PendingTransaction[];
}

interface PendingTransaction {
  tx_id: string;
  outputs: Array<{ address: string; value: number }>;
  total_amount: number;
  fee: number;
  status: string;
  created_at: string;  // ISO format string
  expires_at: string | null;  // ISO format string
  memo: string | null;
}

// Format BCH amount for display (always show 8 decimal places)
const formatBCH = (sats: number) => {
  const bch = sats / 100_000_000;
  return bch.toFixed(8);
};

// Copy to clipboard helper
const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Fallback for older browsers
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    return true;
  }
};

export const EarningsTab: React.FC<EarningsTabProps> = ({
  qubes,
  selectedQubeIds,
  onQubeSelect,
}) => {
  const { userId, password } = useAuth();
  const { invalidateCache } = useWalletCache();
  const [walletInfo, setWalletInfo] = useState<WalletInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [copiedAddress, setCopiedAddress] = useState<string | null>(null);
  const [detailsExpanded, setDetailsExpanded] = useState(false);
  const [receiveExpanded, setReceiveExpanded] = useState(false);
  const [sendExpanded, setSendExpanded] = useState(false);

  // Send form state
  const [sendAddress, setSendAddress] = useState('');
  const [sendAmount, setSendAmount] = useState('');
  const [ownerWif, setOwnerWif] = useState('');
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [sendSuccess, setSendSuccess] = useState<string | null>(null);
  const [refetchTrigger, setRefetchTrigger] = useState(0);

  // Wallet security state (for one-click approval)
  const [walletSecurity, setWalletSecurity] = useState<{
    addresses_with_keys: string[];
    whitelists: Record<string, string[]>;
  }>({ addresses_with_keys: [], whitelists: {} });
  const [approving, setApproving] = useState<string | null>(null);
  const [rejectingTx, setRejectingTx] = useState<string | null>(null);
  const [wifModalOpen, setWifModalOpen] = useState(false);
  const [pendingApprovalTx, setPendingApprovalTx] = useState<PendingTransaction | null>(null);
  const [manualWif, setManualWif] = useState('');

  // Handle copy for balance card addresses
  const handleCopyAddress = async (address: string | undefined) => {
    if (address) {
      await copyToClipboard(address);
      setCopiedAddress(address);
      setTimeout(() => setCopiedAddress(null), 2000);
    }
  };

  // Get the selected qube (use first selected if multiple)
  const selectedQube = qubes.find((q) => selectedQubeIds.includes(q.qube_id));

  // Fetch wallet info when selected qube changes
  useEffect(() => {
    const fetchWalletInfo = async () => {
      if (!selectedQube || !selectedQube.wallet_address || !userId || !password) {
        setWalletInfo(null);
        return;
      }

      setLoading(true);
      setError(null);
      setWalletInfo(null);  // Clear old data so selectedQube addresses show immediately

      try {
        const result = await invoke<{
          success: boolean;
          balance_sats?: number;
          balance_bch?: number;
          wallet_address?: string;
          nft_address?: string;
          nft_balance_sats?: number;
          nft_balance_bch?: number;
          owner_pubkey?: string;
          qube_pubkey?: string;
          pending_transactions?: PendingTransaction[];
          error?: string;
        }>('get_wallet_info', {
          userId,
          qubeId: selectedQube.qube_id,
          password,
        });

        if (result.success) {
          setWalletInfo({
            balance_sats: result.balance_sats || 0,
            balance_bch: result.balance_bch || 0,
            wallet_address: result.wallet_address || selectedQube.wallet_address || '',
            nft_address: result.nft_address,
            nft_balance_sats: result.nft_balance_sats || 0,
            nft_balance_bch: result.nft_balance_bch || 0,
            owner_pubkey: result.owner_pubkey || '',
            qube_pubkey: result.qube_pubkey || '',
            pending_transactions: result.pending_transactions || [],
          });
        } else {
          setError(result.error || 'Failed to fetch wallet info');
        }
      } catch (e) {
        console.error('Failed to fetch wallet info:', e);
        setError('Failed to fetch wallet info');
      } finally {
        setLoading(false);
      }
    };

    fetchWalletInfo();
  }, [selectedQube?.qube_id, userId, password, refetchTrigger]);

  // Handle copy address
  const handleCopy = async () => {
    if (walletInfo?.wallet_address) {
      await copyToClipboard(walletInfo.wallet_address);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // Handle send/withdraw
  const handleSend = async () => {
    if (!selectedQube || !userId || !password || !sendAddress || !sendAmount || !ownerWif) {
      setSendError('Please fill in all fields');
      return;
    }

    const amountSats = Math.floor(parseFloat(sendAmount) * 100_000_000);
    if (isNaN(amountSats) || amountSats <= 0) {
      setSendError('Invalid amount');
      return;
    }

    setSending(true);
    setSendError(null);
    setSendSuccess(null);

    try {
      const result = await invoke<{
        success: boolean;
        txid?: string;
        error?: string;
      }>('owner_withdraw_from_wallet', {
        userId,
        qubeId: selectedQube.qube_id,
        toAddress: sendAddress,
        amount: amountSats,
        ownerWif,
        password,
      });

      if (result.success && result.txid) {
        setSendSuccess(`Transaction sent! TXID: ${result.txid}`);
        setSendAddress('');
        setSendAmount('');
        setOwnerWif('');
        // Invalidate cache and refresh wallet info
        invalidateCache(selectedQube.qube_id);
        // Trigger refetch after a short delay to allow blockchain to update
        setTimeout(() => setRefetchTrigger(prev => prev + 1), 2000);
      } else {
        setSendError(result.error || 'Failed to send transaction');
      }
    } catch (e) {
      console.error('Failed to send:', e);
      setSendError(e instanceof Error ? e.message : 'Failed to send transaction');
    } finally {
      setSending(false);
    }
  };

  // Load wallet security on mount (for one-click approval)
  useEffect(() => {
    const loadWalletSecurity = async () => {
      if (!userId || !password) return;
      try {
        const result = await invoke<{
          success: boolean;
          addresses_with_keys: string[];
          whitelists: Record<string, string[]>;
        }>('get_wallet_security', { userId, password });
        if (result.success) {
          setWalletSecurity({
            addresses_with_keys: result.addresses_with_keys || [],
            whitelists: result.whitelists || {},
          });
        }
      } catch (e) {
        console.error('Failed to load wallet security:', e);
      }
    };
    loadWalletSecurity();
  }, [userId, password]);

  // Check if qube's NFT address (z) has a stored key
  // Use nft_address from walletInfo or recipient_address from qube
  const nftAddress = walletInfo?.nft_address || selectedQube?.recipient_address;
  const hasStoredKey =
    nftAddress && walletSecurity.addresses_with_keys.includes(nftAddress);

  // Approve handler (one-click or manual)
  const handleApprove = async (pendingTx: PendingTransaction) => {
    console.log('[handleApprove] Called with:', { pendingTx, selectedQube: selectedQube?.qube_id, userId, hasPassword: !!password, hasStoredKey, nftAddress });
    if (!selectedQube || !userId || !password) {
      console.log('[handleApprove] Early return - missing:', { selectedQube: !selectedQube, userId: !userId, password: !password });
      return;
    }

    if (hasStoredKey) {
      // One-click approval using stored key
      console.log('[handleApprove] Using stored key for one-click approval');
      setApproving(pendingTx.tx_id);
      try {
        console.log('[handleApprove] Calling approve_wallet_tx_stored_key with:', {
          userId,
          qubeId: selectedQube.qube_id,
          txId: pendingTx.tx_id,
        });
        const result = await invoke<{
          success: boolean;
          txid?: string;
          error?: string;
        }>('approve_wallet_tx_stored_key', {
          userId,
          qubeId: selectedQube.qube_id,
          txId: pendingTx.tx_id,
          password,
        });
        console.log('[handleApprove] Result:', result);
        if (result.success) {
          console.log('[handleApprove] Success! TXID:', result.txid);
          invalidateCache(selectedQube.qube_id);
          setRefetchTrigger((prev) => prev + 1);
        } else {
          console.log('[handleApprove] Failed:', result.error);
          setSendError(result.error || 'Approval failed');
        }
      } catch (e) {
        console.error('[handleApprove] Exception:', e);
        setSendError(e instanceof Error ? e.message : 'Approval failed');
      } finally {
        setApproving(null);
      }
    } else {
      // Show modal to enter WIF manually
      console.log('[handleApprove] Opening WIF modal');
      setPendingApprovalTx(pendingTx);
      setWifModalOpen(true);
    }
  };

  // Manual WIF approval
  const handleManualApprove = async () => {
    if (!pendingApprovalTx || !manualWif || !selectedQube || !userId || !password) return;
    setApproving(pendingApprovalTx.tx_id);
    try {
      const result = await invoke<{
        success: boolean;
        txid?: string;
        error?: string;
      }>('approve_wallet_transaction', {
        userId,
        qubeId: selectedQube.qube_id,
        txId: pendingApprovalTx.tx_id,
        ownerWif: manualWif,
        password,
      });
      if (result.success) {
        setWifModalOpen(false);
        setManualWif('');
        setPendingApprovalTx(null);
        invalidateCache(selectedQube.qube_id);
        setRefetchTrigger((prev) => prev + 1);
      } else {
        setSendError(result.error || 'Approval failed');
      }
    } catch (e) {
      setSendError(e instanceof Error ? e.message : 'Approval failed');
    } finally {
      setApproving(null);
    }
  };

  // Reject handler
  const handleReject = async (pendingTx: PendingTransaction) => {
    if (!selectedQube || !userId || !password) return;
    setRejectingTx(pendingTx.tx_id);
    try {
      await invoke('reject_wallet_transaction', {
        userId,
        qubeId: selectedQube.qube_id,
        txId: pendingTx.tx_id,
        password,
      });
      setRefetchTrigger((prev) => prev + 1);
    } catch (e) {
      setSendError(e instanceof Error ? e.message : 'Reject failed');
    } finally {
      setRejectingTx(null);
    }
  };

  // No qube selected
  if (!selectedQube) {
    return (
      <div className="p-6 flex flex-col items-center justify-center h-full">
        <GlassCard className="p-8 text-center max-w-md">
          <div className="text-4xl mb-4">💰</div>
          <h3 className="text-xl font-semibold text-text-primary mb-2">No Qube Selected</h3>
          <p className="text-text-tertiary">
            Select a Qube from the roster to manage its wallet and view balances.
          </p>
        </GlassCard>
      </div>
    );
  }

  // Qube has no wallet
  if (!selectedQube.wallet_address) {
    return (
      <div className="p-6 flex flex-col items-center justify-center h-full">
        <GlassCard className="p-8 text-center max-w-md">
          <div className="text-4xl mb-4">🔒</div>
          <h3 className="text-xl font-semibold text-text-primary mb-2">No Wallet Configured</h3>
          <p className="text-text-tertiary mb-4">
            {selectedQube.name} does not have a wallet configured. Wallets are created automatically when minting new Qubes.
          </p>
          <p className="text-xs text-text-tertiary">
            To add a wallet, create a new Qube with an owner public key, or re-mint this Qube.
          </p>
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 overflow-y-auto max-h-[calc(100vh-180px)]">
      {/* Wallet Header */}
      <div className="flex items-center gap-4">
        <div
          className="w-16 h-16 rounded-full border-2 flex-shrink-0 shadow-lg"
          style={{
            borderColor: selectedQube.favorite_color,
            boxShadow: `0 0 20px ${selectedQube.favorite_color}40`
          }}
        >
          {selectedQube.avatar_url ? (
            <img
              src={selectedQube.avatar_url}
              alt={selectedQube.name}
              className="w-full h-full rounded-full object-cover"
            />
          ) : (
            <div
              className="w-full h-full rounded-full flex items-center justify-center text-2xl"
              style={{ backgroundColor: selectedQube.favorite_color + '40' }}
            >
              {selectedQube.name.charAt(0).toUpperCase()}
            </div>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="text-2xl font-bold text-text-primary">{selectedQube.name}'s Wallet</h2>
          <p className="text-text-tertiary text-sm mt-1">Manage balances and transactions</p>
        </div>

        {/* Pending Approvals - Top Right */}
        {walletInfo && walletInfo.pending_transactions.length > 0 && (
          <div className="flex-shrink-0">
            <GlassCard className="p-3 border-l-4 border-l-accent-warning">
              <div className="text-xs text-accent-warning font-semibold mb-2 flex items-center gap-1">
                <span>⏳</span> {walletInfo.pending_transactions.length} Pending
              </div>
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {walletInfo.pending_transactions.slice(0, 2).map((tx) => (
                  <div key={tx.tx_id} className="text-xs">
                    <div className="text-text-secondary mb-1">
                      {formatBCH(tx.total_amount)} BCH → {tx.outputs[0]?.address.slice(0, 15)}...
                    </div>
                    <div className="flex gap-1">
                      <button
                        onClick={() => handleApprove(tx)}
                        disabled={approving === tx.tx_id || rejectingTx === tx.tx_id}
                        className="flex-1 px-2 py-1 bg-accent-success/20 text-accent-success text-[10px] rounded hover:bg-accent-success/30 disabled:opacity-50"
                      >
                        {approving === tx.tx_id ? '...' : hasStoredKey ? '✓ Approve' : '🔑 Approve'}
                      </button>
                      <button
                        onClick={() => handleReject(tx)}
                        disabled={approving === tx.tx_id || rejectingTx === tx.tx_id}
                        className="px-2 py-1 bg-red-500/20 text-red-400 text-[10px] rounded hover:bg-red-500/30 disabled:opacity-50"
                      >
                        {rejectingTx === tx.tx_id ? '...' : '✕'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              {walletInfo.pending_transactions.length > 2 && (
                <div className="text-[10px] text-text-tertiary mt-1 text-center">
                  +{walletInfo.pending_transactions.length - 2} more below
                </div>
              )}
            </GlassCard>
          </div>
        )}
      </div>

      {/* Balance Display - Three columns with enhanced styling */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* NFT Address Balance */}
        <GlassCard
          className="p-6 text-center relative overflow-hidden"
          style={{
            background: `linear-gradient(135deg, ${selectedQube.favorite_color}10 0%, transparent 100%)`,
            borderColor: `${selectedQube.favorite_color}30`
          }}
        >
          <div className="absolute inset-0 opacity-20" style={{
            background: `radial-gradient(circle at 50% 0%, ${selectedQube.favorite_color}40 0%, transparent 70%)`
          }} />
          <div className="relative z-10">
            <div className="text-xs text-text-tertiary mb-2 uppercase tracking-wider font-medium">NFT Address</div>
            {loading ? (
              <div className="text-text-tertiary animate-pulse py-4">Loading...</div>
            ) : error ? (
              <div className="text-accent-danger text-sm py-4">{error}</div>
            ) : (
              <>
                <div
                  className="text-3xl font-display font-bold mb-1"
                  style={{
                    color: selectedQube.favorite_color,
                    textShadow: `0 0 20px ${selectedQube.favorite_color}60`
                  }}
                >
                  {formatBCH(walletInfo?.nft_balance_sats || 0)}
                </div>
                <div className="text-text-tertiary text-sm mb-2">BCH</div>
                <div className="text-text-tertiary text-xs">
                  {(walletInfo?.nft_balance_sats || 0).toLocaleString()} sats
                </div>
              </>
            )}
            {(walletInfo?.nft_address || selectedQube.recipient_address) && (
              <div className="mt-3 pt-3 border-t border-glass-border">
                <div className="flex items-center justify-center gap-1">
                  <span className="text-text-tertiary text-[10px] font-mono break-all text-center leading-tight">
                    {walletInfo?.nft_address || selectedQube.recipient_address}
                  </span>
                  <button
                    onClick={() => handleCopyAddress(walletInfo?.nft_address || selectedQube.recipient_address)}
                    className="text-text-tertiary hover:text-text-primary transition-colors p-1 hover:bg-white/10 rounded flex-shrink-0"
                    title="Copy address"
                  >
                    {copiedAddress === (walletInfo?.nft_address || selectedQube.recipient_address) ? '✓' : '📋'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </GlassCard>

        {/* BCH Address Balance */}
        <GlassCard
          className="p-6 text-center relative overflow-hidden"
          style={{
            background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.1) 0%, transparent 100%)',
            borderColor: 'rgba(34, 197, 94, 0.3)'
          }}
        >
          <div className="absolute inset-0 opacity-20" style={{
            background: 'radial-gradient(circle at 50% 0%, rgba(34, 197, 94, 0.4) 0%, transparent 70%)'
          }} />
          <div className="relative z-10">
            <div className="text-xs text-text-tertiary mb-2 uppercase tracking-wider font-medium">BCH Address</div>
            {loading ? (
              <div className="text-text-tertiary animate-pulse py-4">Loading...</div>
            ) : error ? (
              <div className="text-accent-danger text-sm py-4">{error}</div>
            ) : (
              <>
                <div
                  className="text-3xl font-display font-bold mb-1"
                  style={{
                    color: '#22c55e',
                    textShadow: '0 0 20px rgba(34, 197, 94, 0.6)'
                  }}
                >
                  {formatBCH(walletInfo?.nft_balance_sats || 0)}
                </div>
                <div className="text-text-tertiary text-sm mb-2">BCH</div>
                <div className="text-text-tertiary text-xs">
                  {(walletInfo?.nft_balance_sats || 0).toLocaleString()} sats
                </div>
              </>
            )}
            {selectedQube.wallet_owner_q_address && (
              <div className="mt-3 pt-3 border-t border-glass-border">
                <div className="flex items-center justify-center gap-1">
                  <span className="text-text-tertiary text-[10px] font-mono break-all text-center leading-tight">
                    {selectedQube.wallet_owner_q_address}
                  </span>
                  <button
                    onClick={() => handleCopyAddress(selectedQube.wallet_owner_q_address)}
                    className="text-text-tertiary hover:text-text-primary transition-colors p-1 hover:bg-white/10 rounded flex-shrink-0"
                    title="Copy address"
                  >
                    {copiedAddress === selectedQube.wallet_owner_q_address ? '✓' : '📋'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </GlassCard>

        {/* Qube Wallet Balance */}
        <GlassCard
          className="p-6 text-center relative overflow-hidden"
          style={{
            background: 'linear-gradient(135deg, rgba(180, 124, 255, 0.1) 0%, transparent 100%)',
            borderColor: 'rgba(180, 124, 255, 0.3)'
          }}
        >
          <div className="absolute inset-0 opacity-20" style={{
            background: 'radial-gradient(circle at 50% 0%, rgba(180, 124, 255, 0.4) 0%, transparent 70%)'
          }} />
          <div className="relative z-10">
            <div className="text-xs text-text-tertiary mb-2 uppercase tracking-wider font-medium">Qube Wallet</div>
            {loading ? (
              <div className="text-text-tertiary animate-pulse py-4">Loading...</div>
            ) : error ? (
              <div className="text-accent-danger text-sm py-4">{error}</div>
            ) : (
              <>
                <div
                  className="text-3xl font-display font-bold text-accent-secondary mb-1"
                  style={{ textShadow: '0 0 20px rgba(180, 124, 255, 0.6)' }}
                >
                  {formatBCH(walletInfo?.balance_sats || 0)}
                </div>
                <div className="text-text-tertiary text-sm mb-2">BCH</div>
                <div className="text-text-tertiary text-xs">
                  {(walletInfo?.balance_sats || 0).toLocaleString()} sats
                </div>
              </>
            )}
            <div className="mt-3 pt-3 border-t border-glass-border">
              <div className="flex items-center justify-center gap-1">
                <span className="text-text-tertiary text-[10px] font-mono break-all text-center leading-tight">
                  {walletInfo?.wallet_address || selectedQube.wallet_address || ''}
                </span>
                <button
                  onClick={() => handleCopyAddress(walletInfo?.wallet_address || selectedQube.wallet_address)}
                  className="text-text-tertiary hover:text-text-primary transition-colors p-1 hover:bg-white/10 rounded flex-shrink-0"
                  title="Copy address"
                >
                  {copiedAddress === (walletInfo?.wallet_address || selectedQube.wallet_address) ? '✓' : '📋'}
                </button>
              </div>
            </div>
          </div>
        </GlassCard>
      </div>

      {/* Receive & Send - Two column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        {/* Receive Section - Collapsible */}
        <GlassCard className="p-4 border-l-4 border-l-green-500">
          <button
            onClick={() => setReceiveExpanded(!receiveExpanded)}
            className="w-full flex items-center justify-between text-left"
          >
            <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
              <span className="text-xl">📥</span> Receive
            </h3>
            <span
              className="text-text-tertiary text-lg transition-transform duration-200"
              style={{ transform: receiveExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
            >
              ▼
            </span>
          </button>

          {receiveExpanded && (
            <div className="mt-4 pt-4 border-t border-glass-border">
              <div className="flex flex-col items-center gap-4">
                {/* QR Code */}
                <div className="bg-white p-3 rounded-lg shadow-lg">
                  <QRCodeSVG
                    value={walletInfo?.wallet_address || selectedQube.wallet_address || ''}
                    size={120}
                    level="M"
                  />
                </div>
                {/* Address and Copy */}
                <div className="w-full">
                  <p className="text-text-tertiary text-sm mb-2 text-center">Send BCH to this address:</p>
                  <div className="bg-bg-primary p-2 rounded-lg border border-glass-border">
                    <code className="text-xs break-all text-text-primary font-mono block text-center">
                      {walletInfo?.wallet_address || selectedQube.wallet_address}
                    </code>
                  </div>
                  <div className="mt-3 flex justify-center">
                    <GlassButton
                      onClick={handleCopy}
                      variant="secondary"
                      className="text-sm"
                    >
                      {copied ? '✓ Copied!' : '📋 Copy Address'}
                    </GlassButton>
                  </div>
                </div>
              </div>
            </div>
          )}
        </GlassCard>

        {/* Send Section - Collapsible */}
        <GlassCard className="p-4 border-l-4 border-l-red-500">
          <button
            onClick={() => setSendExpanded(!sendExpanded)}
            className="w-full flex items-center justify-between text-left"
          >
            <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
              <span className="text-xl">📤</span> Send
            </h3>
            <span
              className="text-text-tertiary text-lg transition-transform duration-200"
              style={{ transform: sendExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
            >
              ▼
            </span>
          </button>

          {sendExpanded && (
            <div className="mt-4 pt-4 border-t border-glass-border">
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-text-tertiary uppercase tracking-wide block mb-1">
                    Recipient Address
                  </label>
                  <input
                    type="text"
                    value={sendAddress}
                    onChange={(e) => setSendAddress(e.target.value)}
                    placeholder="bitcoincash:q..."
                    className="w-full bg-bg-primary border border-glass-border rounded-lg px-3 py-2 text-sm text-text-primary font-mono placeholder:text-text-disabled focus:outline-none focus:border-accent-secondary"
                  />
                </div>
                <div>
                  <label className="text-xs text-text-tertiary uppercase tracking-wide block mb-1">
                    Amount (BCH)
                  </label>
                  <input
                    type="text"
                    value={sendAmount}
                    onChange={(e) => setSendAmount(e.target.value)}
                    placeholder="0.00000000"
                    className="w-full bg-bg-primary border border-glass-border rounded-lg px-3 py-2 text-sm text-text-primary font-mono placeholder:text-text-disabled focus:outline-none focus:border-accent-secondary"
                  />
                </div>
                <div>
                  <label className="text-xs text-text-tertiary uppercase tracking-wide block mb-1">
                    Owner Private Key (WIF)
                  </label>
                  <input
                    type="password"
                    value={ownerWif}
                    onChange={(e) => setOwnerWif(e.target.value)}
                    placeholder="Enter your WIF private key"
                    className="w-full bg-bg-primary border border-glass-border rounded-lg px-3 py-2 text-sm text-text-primary font-mono placeholder:text-text-disabled focus:outline-none focus:border-accent-secondary"
                  />
                </div>
                {sendError && (
                  <div className="text-accent-danger text-sm bg-accent-danger/10 p-2 rounded">
                    {sendError}
                  </div>
                )}
                {sendSuccess && (
                  <div className="text-accent-success text-sm bg-accent-success/10 p-2 rounded break-all">
                    {sendSuccess}
                  </div>
                )}
                <GlassButton
                  onClick={handleSend}
                  disabled={sending || !sendAddress || !sendAmount || !ownerWif}
                  className="w-full"
                >
                  {sending ? 'Sending...' : '📤 Send Transaction'}
                </GlassButton>
                <p className="text-xs text-text-tertiary">
                  This uses the owner-only spending path. No Qube signature required.
                </p>
              </div>
            </div>
          )}
        </GlassCard>
      </div>

      {/* Transaction History & Wallet Details - Side by Side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
        {/* Transaction History */}
        {walletInfo && (
          <TransactionHistory
            qubeId={selectedQube.qube_id}
            walletAddress={walletInfo.wallet_address}
          />
        )}

        {/* Wallet Details - Collapsible */}
        <GlassCard className="p-4 h-fit border-l-4 border-l-sky-500">
          <button
            onClick={() => setDetailsExpanded(!detailsExpanded)}
            className="w-full flex items-center justify-between text-left"
          >
            <h3 className="text-md font-semibold text-text-primary flex items-center gap-2">
              <span>ℹ️</span> Wallet Details
            </h3>
            <span className="text-text-tertiary text-lg transition-transform duration-200" style={{
              transform: detailsExpanded ? 'rotate(180deg)' : 'rotate(0deg)'
            }}>
              ▼
            </span>
          </button>

          {detailsExpanded && (
            <div className="mt-4 pt-4 border-t border-glass-border">
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-text-tertiary">Type:</span>
                  <span className="text-text-primary">Asymmetric Multi-Sig (2-of-2)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-tertiary">Spending Rules:</span>
                  <span className="text-text-primary">Owner + Qube required</span>
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-text-tertiary">Owner Pubkey:</span>
                  <span className="text-text-primary font-mono text-xs break-all">
                    {walletInfo?.owner_pubkey}
                  </span>
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-text-tertiary">Qube Pubkey:</span>
                  <span className="text-text-primary font-mono text-xs break-all">
                    {walletInfo?.qube_pubkey}
                  </span>
                </div>
              </div>
              <div className="mt-4 p-3 bg-accent-primary/10 rounded-lg border border-accent-primary/30">
                <p className="text-xs text-text-secondary">
                  <strong>Security Note:</strong> The Qube cannot spend funds without your approval.
                  You can withdraw funds at any time using the owner-only spending path.
                </p>
              </div>
            </div>
          )}
        </GlassCard>
      </div>

      {/* WIF Modal for manual approval */}
      {wifModalOpen && pendingApprovalTx && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <GlassCard className="p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
              <span>🔑</span> Enter Owner WIF to Approve
            </h3>
            <p className="text-sm text-text-secondary mb-4">
              Approve sending {formatBCH(pendingApprovalTx.total_amount)} BCH to{' '}
              {pendingApprovalTx.outputs[0]?.address.slice(0, 20)}...
            </p>
            <input
              type="password"
              value={manualWif}
              onChange={(e) => setManualWif(e.target.value)}
              placeholder="Enter WIF private key"
              className="w-full bg-bg-primary border border-glass-border rounded-lg px-3 py-2 text-sm text-text-primary font-mono mb-4 focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
            />
            <p className="text-[10px] text-text-tertiary mb-4">
              Tip: Store your key in Dashboard → Qube Card → Wallet Security to enable one-click approvals.
            </p>
            <div className="flex gap-2">
              <GlassButton
                onClick={() => {
                  setWifModalOpen(false);
                  setManualWif('');
                  setPendingApprovalTx(null);
                }}
                variant="secondary"
                className="flex-1"
              >
                Cancel
              </GlassButton>
              <GlassButton
                onClick={handleManualApprove}
                disabled={!manualWif || approving !== null}
                className="flex-1"
                variant="primary"
              >
                {approving ? 'Approving...' : 'Approve'}
              </GlassButton>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
};

export default EarningsTab;
