import React, { useState, useEffect, useCallback, useRef } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { GlassCard, GlassButton } from '../glass';
import { useAuth } from '../../hooks/useAuth';
import { useWalletCache } from '../../hooks/useWalletCache';
import { TransactionHistoryEntry, TransactionHistoryResponse } from '../../types';

interface TransactionHistoryProps {
  qubeId: string;
  walletAddress: string;
}

// Format BCH amount
const formatBCH = (sats: number) => {
  const bch = Math.abs(sats) / 100_000_000;
  return bch.toFixed(8);
};

// Format timestamp for display
const formatTimestamp = (isoString: string) => {
  const date = new Date(isoString);
  return date.toLocaleString();
};

// Get transaction type styling
const getTxTypeStyle = (txType: string) => {
  switch (txType) {
    case 'deposit':
      return { color: '#22c55e', icon: '📥', label: 'Received' };
    case 'withdrawal':
      return { color: '#ef4444', icon: '📤', label: 'Sent' };
    case 'qube_spend':
      return { color: '#f59e0b', icon: '🤖', label: 'Qube Spend' };
    default:
      return { color: '#6b7280', icon: '💱', label: 'Transaction' };
  }
};

// Get confirmation status styling
const getConfirmationStyle = (isConfirmed: boolean, confirmations: number) => {
  if (!isConfirmed || confirmations === 0) {
    return {
      color: '#ef4444',
      bgColor: 'rgba(239, 68, 68, 0.15)',
      borderColor: 'rgba(239, 68, 68, 0.4)',
      label: 'Unconfirmed',
      icon: '⏳',
      pulse: true,
    };
  }
  if (confirmations < 3) {
    return {
      color: '#f59e0b',
      bgColor: 'rgba(245, 158, 11, 0.15)',
      borderColor: 'rgba(245, 158, 11, 0.4)',
      label: `${confirmations} confirmation${confirmations > 1 ? 's' : ''}`,
      icon: '🔄',
      pulse: false,
    };
  }
  if (confirmations < 6) {
    return {
      color: '#eab308',
      bgColor: 'rgba(234, 179, 8, 0.15)',
      borderColor: 'rgba(234, 179, 8, 0.4)',
      label: `${confirmations} confirmations`,
      icon: '⏱️',
      pulse: false,
    };
  }
  // 6+ confirmations = fully confirmed
  return {
    color: '#22c55e',
    bgColor: 'rgba(34, 197, 94, 0.15)',
    borderColor: 'rgba(34, 197, 94, 0.4)',
    label: `${confirmations} confirmed`,
    icon: '✓',
    pulse: false,
  };
};

export const TransactionHistory: React.FC<TransactionHistoryProps> = ({
  qubeId,
  walletAddress,
}) => {
  const { userId, password } = useAuth();
  const { getWalletData, setTransactions: setCachedTransactions, setError: setCachedError } = useWalletCache();

  // Get cached data
  const cachedData = getWalletData(qubeId);

  const [transactions, setTransactions] = useState<TransactionHistoryEntry[]>(
    cachedData?.transactions || []
  );
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(cachedData?.error || null);
  const [hasMore, setHasMore] = useState(cachedData?.hasMoreTx || false);
  const [totalCount, setTotalCount] = useState(cachedData?.totalTxCount || 0);
  const [expanded, setExpanded] = useState(false);
  const [visibleCount, setVisibleCount] = useState(5);

  // Track if we've already fetched for this qubeId
  const hasFetchedRef = useRef<string | null>(null);

  // Polling for unconfirmed transactions
  const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollingQubeIdRef = useRef<string | null>(null); // Track which qube we're polling for
  const POLL_INTERVAL_MS = 30000; // Check every 30 seconds

  const PAGE_SIZE = 20;
  const SHOW_INCREMENT = 5;

  const fetchTransactions = useCallback(async (offset: number = 0, append: boolean = false, forceRefresh: boolean = false) => {
    if (!userId || !password || !qubeId) return;

    // Skip fetch if we have cached data and this isn't a refresh or load-more
    if (!forceRefresh && offset === 0 && cachedData && cachedData.transactions && cachedData.transactions.length > 0) {
      // Use cached data
      setTransactions(cachedData.transactions);
      setTotalCount(cachedData.totalTxCount);
      setHasMore(cachedData.hasMoreTx);
      return;
    }

    if (offset === 0) {
      setLoading(true);
    } else {
      setLoadingMore(true);
    }
    setError(null);

    try {
      const result = await invoke<TransactionHistoryResponse>('get_wallet_transactions', {
        userId,
        qubeId,
        password,
        limit: PAGE_SIZE,
        offset,
      });

      if (result.success) {
        const txList = result.transactions || [];
        if (append) {
          setTransactions(prev => [...prev, ...txList]);
          // Update cache with appended transactions
          setCachedTransactions(
            qubeId,
            [...transactions, ...txList],
            result.total_count || 0,
            result.has_more || false,
            false
          );
        } else {
          setTransactions(txList);
          // Update cache
          setCachedTransactions(
            qubeId,
            txList,
            result.total_count || 0,
            result.has_more || false,
            false
          );
        }
        setHasMore(result.has_more || false);
        setTotalCount(result.total_count || 0);

        // Debug: log if count mismatches
        if ((result.total_count || 0) > 0 && txList.length === 0) {
          console.warn('Transaction count mismatch: total_count =', result.total_count, 'but transactions array is empty');
        }
      } else {
        const errorMsg = result.error || 'Failed to fetch transaction history';
        setError(errorMsg);
        setCachedError(qubeId, errorMsg);
      }
    } catch (e) {
      console.error('Failed to fetch transactions:', e);
      const errorMsg = 'Failed to fetch transaction history';
      setError(errorMsg);
      setCachedError(qubeId, errorMsg);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [userId, password, qubeId, cachedData, transactions, setCachedTransactions, setCachedError]);

  useEffect(() => {
    // Only fetch if we haven't fetched for this qubeId yet and don't have cached data
    if (hasFetchedRef.current !== qubeId && (!cachedData || cachedData.transactions.length === 0)) {
      hasFetchedRef.current = qubeId;
      fetchTransactions(0, false, true);
    } else if (cachedData && cachedData.transactions.length > 0) {
      // Sync local state with cache
      setTransactions(cachedData.transactions);
      setTotalCount(cachedData.totalTxCount);
      setHasMore(cachedData.hasMoreTx);
    }
  }, [qubeId, cachedData, fetchTransactions]);

  // Check if there are any unconfirmed transactions
  const hasUnconfirmed = transactions.some(tx => !tx.is_confirmed || tx.confirmations < 6);

  // Stable ref for the fetch function to avoid resetting interval
  const fetchRef = useRef(fetchTransactions);
  fetchRef.current = fetchTransactions;

  // Polling effect for unconfirmed transactions
  useEffect(() => {
    // Clear existing interval if qubeId changed
    if (pollingQubeIdRef.current && pollingQubeIdRef.current !== qubeId) {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    }

    // Only start/stop polling based on expanded state and unconfirmed status
    // Don't react to loading state to avoid resetting the interval during fetches
    if (expanded && hasUnconfirmed && qubeId) {
      // Only set up interval if we don't already have one for this qube
      if (!pollingIntervalRef.current) {
        pollingQubeIdRef.current = qubeId;
        pollingIntervalRef.current = setInterval(() => {
          // Use ref to get current fetch function without adding to deps
          fetchRef.current(0, false, true);
        }, POLL_INTERVAL_MS);
      }
    } else {
      // Stop polling if collapsed or all transactions are confirmed
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
        pollingQubeIdRef.current = null;
      }
    }

    // Cleanup on unmount
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
        pollingQubeIdRef.current = null;
      }
    };
  }, [expanded, hasUnconfirmed, qubeId]);

  const handleLoadMore = () => {
    fetchTransactions(transactions.length, true, true);
  };

  const handleRefresh = () => {
    fetchTransactions(0, false, true);
  };

  return (
    <GlassCard className="p-4 border-l-4 border-l-amber-500">
      {/* Header with toggle */}
      <button
        onClick={() => {
          if (expanded) {
            // Reset visible count when collapsing
            setVisibleCount(5);
          }
          setExpanded(!expanded);
        }}
        className="w-full flex items-center justify-between text-left"
      >
        <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
          <span>📜</span> Transaction History
          {totalCount > 0 && (
            <span className="text-sm font-normal text-text-tertiary">
              ({totalCount} transactions)
            </span>
          )}
        </h3>
        <span
          className="text-text-tertiary text-lg transition-transform duration-200"
          style={{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
        >
          ▼
        </span>
      </button>

      {expanded && (
        <div className="mt-4 pt-4 border-t border-glass-border">
          {/* Refresh and Show All buttons */}
          <div className="flex justify-between items-center mb-3">
            {/* Auto-refresh indicator */}
            <div className="flex items-center gap-2">
              {hasUnconfirmed && (
                <span className="text-xs text-text-tertiary flex items-center gap-1">
                  <span className="inline-block w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
                  Auto-refreshing
                </span>
              )}
            </div>

            <div className="flex gap-2">
              {transactions.length > visibleCount && (
                <GlassButton
                  onClick={() => setVisibleCount(transactions.length)}
                  variant="ghost"
                  size="sm"
                >
                  Show All
                </GlassButton>
              )}
              <GlassButton
                onClick={handleRefresh}
                variant="ghost"
                size="sm"
                disabled={loading}
              >
                {loading ? 'Loading...' : 'Refresh'}
              </GlassButton>
            </div>
          </div>

          {/* Error state */}
          {error && (
            <div className="text-accent-danger text-sm bg-accent-danger/10 p-3 rounded mb-4">
              {error}
            </div>
          )}

          {/* Loading state */}
          {loading && transactions.length === 0 && (
            <div className="text-text-tertiary text-center py-8 animate-pulse">
              Loading transaction history...
            </div>
          )}

          {/* Empty state */}
          {!loading && transactions.length === 0 && !error && (
            <div className="text-text-tertiary text-center py-8">
              <div className="text-4xl mb-2">📭</div>
              <p>No transactions yet</p>
              <p className="text-sm mt-1">
                Send BCH to your wallet address to get started
              </p>
            </div>
          )}

          {/* Transaction list */}
          {transactions.length > 0 && (
            <div className="space-y-2">
              {/* Reverse to show newest first, then limit to visibleCount */}
              {[...transactions].reverse().slice(0, visibleCount).map((tx) => {
                const typeStyle = getTxTypeStyle(tx.tx_type);
                const confStyle = getConfirmationStyle(tx.is_confirmed, tx.confirmations);
                const isPositive = tx.amount > 0;

                return (
                  <div
                    key={tx.txid}
                    className="p-3 bg-bg-primary rounded-lg border-l-4 border border-glass-border hover:border-accent-primary/30 transition-colors"
                    style={{ borderLeftColor: typeStyle.color }}
                  >
                    <div className="flex justify-between items-start">
                      {/* Left: Type and details */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <span>{typeStyle.icon}</span>
                          <span
                            className="text-sm font-medium"
                            style={{ color: typeStyle.color }}
                          >
                            {typeStyle.label}
                          </span>
                          {/* Confirmation status badge - always shown */}
                          <span
                            className={`text-xs px-2 py-0.5 rounded-full flex items-center gap-1 ${confStyle.pulse ? 'animate-pulse' : ''}`}
                            style={{
                              backgroundColor: confStyle.bgColor,
                              color: confStyle.color,
                              border: `1px solid ${confStyle.borderColor}`,
                            }}
                          >
                            <span>{confStyle.icon}</span>
                            <span>{confStyle.label}</span>
                          </span>
                        </div>

                        {/* Counterparty - show Qube name if available */}
                        {(tx.counterparty || tx.counterparty_qube_name) && (
                          <div className="text-xs text-text-tertiary">
                            {isPositive ? 'From: ' : 'To: '}
                            {tx.counterparty_qube_name ? (
                              <span className="text-accent-primary font-medium">
                                {tx.counterparty_qube_name}
                              </span>
                            ) : (
                              <span className="font-mono break-all">{tx.counterparty}</span>
                            )}
                            {/* Show address on hover or as secondary info if we have qube name */}
                            {tx.counterparty_qube_name && tx.counterparty && (
                              <span className="font-mono text-text-disabled ml-1">
                                ({tx.counterparty.slice(0, 20)}...)
                              </span>
                            )}
                          </div>
                        )}

                        {/* Memo */}
                        {tx.memo && (
                          <div className="text-xs text-text-secondary mt-1 italic">
                            "{tx.memo}"
                          </div>
                        )}

                        {/* Timestamp */}
                        <div className="text-xs text-text-tertiary mt-1">
                          {formatTimestamp(tx.timestamp)}
                        </div>
                      </div>

                      {/* Right: Amount */}
                      <div className="text-right flex-shrink-0 ml-4">
                        <div
                          className="font-mono font-semibold"
                          style={{ color: isPositive ? '#22c55e' : '#ef4444' }}
                        >
                          {isPositive ? '+' : '-'}{formatBCH(tx.amount)} BCH
                        </div>
                        <div className="text-xs text-text-tertiary">
                          {Math.abs(tx.amount).toLocaleString()} sats
                        </div>
                        {tx.fee > 0 && (
                          <div className="text-xs text-text-disabled">
                            Fee: {tx.fee} sats
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Transaction link */}
                    <div className="mt-2 pt-2 border-t border-glass-border/50 flex justify-between items-center">
                      <span className="text-xs text-text-disabled font-mono break-all">
                        {tx.txid}
                      </span>
                      <a
                        href={tx.explorer_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-accent-primary hover:text-accent-primary/80 transition-colors"
                      >
                        View on Explorer →
                      </a>
                    </div>
                  </div>
                );
              })}

              {/* Show more button - shows 5 more at a time */}
              {visibleCount < transactions.length && (
                <div className="pt-4 text-center">
                  <GlassButton
                    onClick={() => setVisibleCount(prev => Math.min(prev + SHOW_INCREMENT, transactions.length))}
                    variant="secondary"
                  >
                    Show More ({transactions.length - visibleCount} remaining)
                  </GlassButton>
                </div>
              )}

              {/* Load more from server - only show when all local are visible and server has more */}
              {visibleCount >= transactions.length && hasMore && (
                <div className="pt-4 text-center">
                  <GlassButton
                    onClick={handleLoadMore}
                    variant="secondary"
                    disabled={loadingMore}
                  >
                    {loadingMore ? 'Loading...' : 'Load More from Server'}
                  </GlassButton>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </GlassCard>
  );
};

export default TransactionHistory;
