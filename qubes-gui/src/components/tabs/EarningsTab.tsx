import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { QRCodeSVG } from 'qrcode.react';
import { Qube } from '../../types';
import { GlassCard, GlassButton } from '../glass';
import { useAuth } from '../../hooks/useAuth';
import { useWallet } from '../../contexts/WalletContext';
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
  const wallet = useWallet();
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
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [sendSuccess, setSendSuccess] = useState<string | null>(null);
  const [refetchTrigger, setRefetchTrigger] = useState(0);

  // Approval state
  const [approving, setApproving] = useState<string | null>(null);
  const [rejectingTx, setRejectingTx] = useState<string | null>(null);
  const [approvalError, setApprovalError] = useState<string | null>(null);

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

  // Find the WC session that owns this qube (by matching owner pubkey)
  const qubeSession = wallet.getSessionForQube(walletInfo?.owner_pubkey || selectedQube?.wallet_owner_pubkey);
  const qubeWalletConnected = !!qubeSession;
  const qubeWalletAddress = qubeSession?.address || null;

  // Fetch wallet info when selected qube changes
  useEffect(() => {
    const fetchWalletInfo = async (isBackgroundRefresh = false) => {
      if (!selectedQube || !selectedQube.wallet_address || !userId || !password) {
        setWalletInfo(null);
        return;
      }

      // Only show loading state for initial loads, not background refreshes
      if (!isBackgroundRefresh) {
        setLoading(true);
        setError(null);
        setWalletInfo(null);  // Clear old data so selectedQube addresses show immediately
      }

      try {
        const result = await invoke<{
          success: boolean;
          balance_sats?: number;
          balance_bch?: number;
          wallet_address?: string;
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
            owner_pubkey: result.owner_pubkey || '',
            qube_pubkey: result.qube_pubkey || '',
            pending_transactions: result.pending_transactions || [],
          });
        } else if (!isBackgroundRefresh) {
          // Only show errors for initial loads, not background refreshes
          setError(result.error || 'Failed to fetch wallet info');
        }
      } catch (e) {
        console.error('Failed to fetch wallet info:', e);
        if (!isBackgroundRefresh) {
          setError('Failed to fetch wallet info');
        }
      } finally {
        if (!isBackgroundRefresh) {
          setLoading(false);
        }
      }
    };

    // Initial fetch (refetchTrigger starts at 0)
    if (refetchTrigger === 0) {
      fetchWalletInfo(false);
    } else {
      // Background refresh (silent)
      fetchWalletInfo(true);
    }
  }, [selectedQube?.qube_id, userId, password, refetchTrigger]);

  // Auto-refresh pending transactions every 30 seconds (silent)
  useEffect(() => {
    if (!selectedQube || !userId || !password) return;

    const intervalId = setInterval(() => {
      // Silently refetch to check for new pending transactions
      setRefetchTrigger(prev => prev + 1);
    }, 30000); // 30 seconds (less aggressive)

    return () => clearInterval(intervalId);
  }, [selectedQube?.qube_id, userId, password]);

  // Handle copy address
  const handleCopy = async () => {
    if (walletInfo?.wallet_address) {
      await copyToClipboard(walletInfo.wallet_address);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // Handle send via WalletConnect
  const handleSend = async () => {
    if (!selectedQube || !userId || !password || !sendAddress || !sendAmount || !qubeWalletConnected || !qubeWalletAddress || !qubeSession) {
      setSendError('WalletConnect not connected for this qube, or missing fields');
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
      // Step 1: Prepare WC transaction on backend
      const prepResult = await invoke<{
        success: boolean;
        wc_transaction?: string;
        error?: string;
      }>('prepare_owner_withdraw_wc', {
        userId,
        qubeId: selectedQube.qube_id,
        toAddress: sendAddress,
        amount: amountSats,
        ownerAddress: qubeWalletAddress,
        password,
      });

      if (!prepResult.success || !prepResult.wc_transaction) {
        setSendError(prepResult.error || 'Failed to prepare WC transaction');
        return;
      }

      // Step 2: Send to wallet for signing + broadcast via the qube's specific session
      const signResult = await wallet.signTransactionWith(qubeSession!.topic, prepResult.wc_transaction);

      // Step 3: Record the broadcast in backend
      await invoke('record_wallet_broadcast', {
        userId,
        qubeId: selectedQube.qube_id,
        txid: signResult.signedTransactionHash,
        toAddress: sendAddress,
        amount: amountSats,
        memo: 'WalletConnect withdrawal',
        password,
      });

      setSendSuccess(`Transaction sent via WalletConnect! TXID: ${signResult.signedTransactionHash}`);
      setSendAddress('');
      setSendAmount('');
      invalidateCache(selectedQube.qube_id);
      setTimeout(() => setRefetchTrigger(prev => prev + 1), 2000);
    } catch (e) {
      console.error('WC send failed:', e);
      const msg = e instanceof Error ? e.message : 'WalletConnect transaction failed';
      setSendError(msg.includes('rejected') ? 'Transaction rejected by wallet' : msg);
    } finally {
      setSending(false);
    }
  };

  // Handle approve via WalletConnect
  const handleApprove = async (pendingTx: PendingTransaction) => {
    if (!selectedQube || !userId || !password || !qubeWalletConnected || !qubeWalletAddress || !qubeSession) {
      setApprovalError('Connect the wallet that owns this qube to approve transactions');
      setTimeout(() => setApprovalError(null), 5000);
      return;
    }

    setApproving(pendingTx.tx_id);
    setApprovalError(null);

    try {
      const prepResult = await invoke<{
        success: boolean;
        wc_transaction?: string;
        error?: string;
      }>('prepare_approve_tx_wc', {
        userId,
        qubeId: selectedQube.qube_id,
        txId: pendingTx.tx_id,
        ownerAddress: qubeWalletAddress,
        password,
      });

      if (!prepResult.success || !prepResult.wc_transaction) {
        setApprovalError(prepResult.error || 'Failed to prepare approval');
        setTimeout(() => setApprovalError(null), 8000);
        return;
      }

      const signResult = await wallet.signTransactionWith(qubeSession!.topic, prepResult.wc_transaction);

      await invoke('record_wallet_broadcast', {
        userId,
        qubeId: selectedQube.qube_id,
        txid: signResult.signedTransactionHash,
        toAddress: pendingTx.outputs[0]?.address || '',
        amount: pendingTx.total_amount,
        memo: pendingTx.memo || 'Approved transaction',
        password,
      });

      invalidateCache(selectedQube.qube_id);
      setRefetchTrigger((prev) => prev + 1);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Approval failed';
      setApprovalError(msg.includes('rejected') ? 'Rejected by wallet' : msg.length > 60 ? msg.slice(0, 60) + '...' : msg);
      setTimeout(() => setApprovalError(null), 8000);
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
              {approvalError && (
                <div className="text-[10px] text-red-400 bg-red-500/10 px-2 py-1 rounded mb-2 break-words">
                  {approvalError}
                </div>
              )}
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {walletInfo.pending_transactions.slice(0, 2).map((tx) => (
                  <div key={tx.tx_id} className="text-xs">
                    <div className="text-text-secondary mb-1">
                      {formatBCH(tx.total_amount)} BCH → {tx.outputs[0]?.address.slice(0, 15)}...
                    </div>
                    <div className="flex gap-1">
                      <button
                        onClick={() => handleApprove(tx)}
                        disabled={approving === tx.tx_id || rejectingTx === tx.tx_id || !qubeWalletConnected}
                        className="flex-1 px-2 py-1 bg-accent-success/20 text-accent-success text-[10px] rounded hover:bg-accent-success/30 disabled:opacity-50"
                        title={!qubeWalletConnected ? 'Connect the wallet that owns this qube' : ''}
                      >
                        {approving === tx.tx_id ? '...' : qubeWalletConnected ? '📱 Approve' : '📱 Connect'}
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

      {/* Wallet Balance */}
      <div className="max-w-md mx-auto">
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
            <div className="text-xs text-text-tertiary mb-2 uppercase tracking-wider font-medium">Qube Wallet</div>
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
                {qubeWalletConnected ? (
                  <div className="flex items-center gap-2 text-sm text-accent-primary bg-accent-primary/10 p-2 rounded">
                    <span>Wallet: {qubeWalletAddress?.slice(0, 20)}...</span>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-sm text-accent-warning bg-accent-warning/10 p-2 rounded">
                    <span>Connect the wallet that owns this qube via WalletConnect</span>
                  </div>
                )}
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
                  disabled={sending || !sendAddress || !sendAmount || !qubeWalletConnected}
                  className="w-full"
                >
                  {sending ? 'Signing...' : '📤 Sign with Wallet'}
                </GlassButton>
                <p className="text-xs text-text-tertiary">
                  Your connected wallet signs the transaction. No private keys needed.
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
                  <span className="text-text-primary">CashScript Contract (P2SH32)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-tertiary">Spending Paths:</span>
                  <span className="text-text-primary">Owner-only or Qube+Owner</span>
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
                  <strong>Security Note:</strong> The Qube cannot spend funds without your wallet approval.
                  You can withdraw funds at any time by signing with your connected wallet.
                </p>
              </div>
            </div>
          )}
        </GlassCard>
      </div>

    </div>
  );
};

export default EarningsTab;
