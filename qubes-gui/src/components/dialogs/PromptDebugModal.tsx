import React, { useState, useEffect, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { GlassCard, GlassButton } from '../glass';
import { useQubeSelection } from '../../hooks/useQubeSelection';
import { useAuth } from '../../hooks/useAuth';

interface DebugPromptInfo {
  qube_id: string;
  qube_name: string;
  messages: Array<{
    role: string;
    content: string;
    tool_calls?: unknown[];
  }>;
  model: string;
  provider: string;
  timestamp: string;
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
  response: string | null;
}

type TabType = 'prompt' | 'raw_chain_state' | 'ai_chain_state' | 'formatted_chain_state';

// Helper to format timestamps
const formatTimestamp = (ts: number | string | null | undefined): string => {
  if (!ts) return 'Never';
  const date = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts);
  if (isNaN(date.getTime())) return String(ts);
  return date.toLocaleString();
};

// Helper to format BCH amounts
const formatBCH = (sats: number | undefined): string => {
  if (!sats) return '0 BCH';
  const bch = sats / 100_000_000;
  if (bch < 0.0001) return `${sats.toLocaleString()} sats`;
  return `${bch.toFixed(8)} BCH`;
};

// Section icons and colors
const sectionConfig: Record<string, { icon: string; color: string; label: string }> = {
  chain: { icon: '🔗', color: 'emerald', label: 'Blockchain' },
  session: { icon: '⚡', color: 'yellow', label: 'Current Session' },
  settings: { icon: '⚙️', color: 'blue', label: 'Settings' },
  runtime: { icon: '🔄', color: 'purple', label: 'Runtime' },
  stats: { icon: '📊', color: 'cyan', label: 'Statistics' },
  block_counts: { icon: '📦', color: 'orange', label: 'Block Counts' },
  skills: { icon: '🎯', color: 'pink', label: 'Skills' },
  relationships: { icon: '👥', color: 'indigo', label: 'Relationships' },
  financial: { icon: '💰', color: 'green', label: 'Financial' },
  mood: { icon: '😊', color: 'amber', label: 'Mood' },
  owner_info: { icon: '👤', color: 'teal', label: 'Owner Info' },
  health: { icon: '💚', color: 'lime', label: 'Health' },
  attestation: { icon: '🔒', color: 'slate', label: 'Attestation' },
};

interface PromptDebugModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PromptDebugModal: React.FC<PromptDebugModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [promptInfo, setPromptInfo] = useState<DebugPromptInfo | null>(null);
  const [rawChainState, setRawChainState] = useState<Record<string, unknown> | null>(null);
  const [aiChainState, setAiChainState] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [expandedMessages, setExpandedMessages] = useState<Set<number>>(new Set());
  const [activeTab, setActiveTab] = useState<TabType>('prompt');
  const { activeQubeByTab, currentTab } = useQubeSelection();
  const { userId, password } = useAuth();
  const selectedQubeId = activeQubeByTab[currentTab];

  const fetchPrompt = useCallback(async () => {
    if (!selectedQubeId) {
      setError('No qube selected');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await invoke<{ success: boolean; prompt?: DebugPromptInfo; error?: string }>(
        'get_debug_prompt',
        { qubeId: selectedQubeId }
      );

      if (result.success && result.prompt) {
        setPromptInfo(result.prompt);
      } else {
        setError(result.error || 'No prompt cached for this qube');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch prompt');
    } finally {
      setLoading(false);
    }
  }, [selectedQubeId]);

  const fetchChainState = useCallback(async () => {
    if (!selectedQubeId || !userId || !password) {
      return;
    }

    try {
      const result = await invoke<{
        success: boolean;
        raw_chain_state?: Record<string, unknown>;
        active_context?: Record<string, unknown>;
        error?: string
      }>(
        'get_context_preview',
        { userId, qubeId: selectedQubeId, password }
      );

      if (result.success) {
        if (result.raw_chain_state) {
          setRawChainState(result.raw_chain_state);
        }
        if (result.active_context) {
          setAiChainState(result.active_context);
        }
      }
    } catch (err) {
      console.error('Failed to fetch chain state:', err);
    }
  }, [selectedQubeId, userId, password]);

  useEffect(() => {
    if (isOpen && selectedQubeId) {
      fetchPrompt();
      fetchChainState();
    }
  }, [isOpen, selectedQubeId, fetchPrompt, fetchChainState]);

  const toggleMessage = (index: number) => {
    setExpandedMessages(prev => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const formatTokens = (tokens: number | null) => {
    if (tokens === null) return '-';
    return tokens.toLocaleString();
  };

  const copyToClipboard = async () => {
    if (activeTab === 'prompt' && promptInfo) {
      const text = JSON.stringify(promptInfo, null, 2);
      await navigator.clipboard.writeText(text);
    } else if (activeTab === 'raw_chain_state' && rawChainState) {
      const text = JSON.stringify(rawChainState, null, 2);
      await navigator.clipboard.writeText(text);
    } else if (activeTab === 'ai_chain_state' && aiChainState) {
      const text = JSON.stringify(aiChainState, null, 2);
      await navigator.clipboard.writeText(text);
    } else if (activeTab === 'formatted_chain_state' && rawChainState) {
      const text = JSON.stringify(rawChainState, null, 2);
      await navigator.clipboard.writeText(text);
    }
  };

  const getCopyButtonDisabled = () => {
    if (activeTab === 'prompt') return !promptInfo;
    if (activeTab === 'raw_chain_state') return !rawChainState;
    if (activeTab === 'ai_chain_state') return !aiChainState;
    if (activeTab === 'formatted_chain_state') return !rawChainState;
    return true;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <GlassCard className="w-full max-w-4xl max-h-[90vh] p-6 m-4 overflow-hidden flex flex-col">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-display text-accent-primary">
            Debug Inspector
          </h2>
          <div className="flex gap-2">
            <GlassButton
              variant="secondary"
              onClick={() => { fetchPrompt(); fetchChainState(); }}
              disabled={loading}
            >
              Refresh
            </GlassButton>
            <GlassButton
              variant="secondary"
              onClick={copyToClipboard}
              disabled={getCopyButtonDisabled()}
            >
              Copy JSON
            </GlassButton>
            <GlassButton
              variant="secondary"
              onClick={onClose}
            >
              Close
            </GlassButton>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-4 border-b border-glass-border pb-2">
          <button
            onClick={() => setActiveTab('prompt')}
            className={`px-4 py-2 rounded-t-lg transition-colors ${
              activeTab === 'prompt'
                ? 'bg-purple-500/20 text-purple-300 border-b-2 border-purple-400'
                : 'text-text-secondary hover:text-text-primary hover:bg-glass-bg/50'
            }`}
          >
            System Prompt
          </button>
          <button
            onClick={() => setActiveTab('raw_chain_state')}
            className={`px-4 py-2 rounded-t-lg transition-colors ${
              activeTab === 'raw_chain_state'
                ? 'bg-amber-500/20 text-amber-300 border-b-2 border-amber-400'
                : 'text-text-secondary hover:text-text-primary hover:bg-glass-bg/50'
            }`}
          >
            Raw Chain State
          </button>
          <button
            onClick={() => setActiveTab('ai_chain_state')}
            className={`px-4 py-2 rounded-t-lg transition-colors ${
              activeTab === 'ai_chain_state'
                ? 'bg-cyan-500/20 text-cyan-300 border-b-2 border-cyan-400'
                : 'text-text-secondary hover:text-text-primary hover:bg-glass-bg/50'
            }`}
          >
            AI Chain State
          </button>
          <button
            onClick={() => setActiveTab('formatted_chain_state')}
            className={`px-4 py-2 rounded-t-lg transition-colors ${
              activeTab === 'formatted_chain_state'
                ? 'bg-emerald-500/20 text-emerald-300 border-b-2 border-emerald-400'
                : 'text-text-secondary hover:text-text-primary hover:bg-glass-bg/50'
            }`}
          >
            Formatted
          </button>
        </div>

        {loading && (
          <div className="text-text-secondary text-center py-8">Loading...</div>
        )}

        {error && activeTab === 'prompt' && (
          <div className="text-red-400 text-center py-8">{error}</div>
        )}

        {/* Raw Chain State Tab */}
        {activeTab === 'raw_chain_state' && !loading && (
          <div className="overflow-y-auto flex-1">
            <div className="text-xs text-amber-400 mb-2 px-1">
              Unmodified chain_state.json contents (what's stored on disk)
            </div>
            {rawChainState ? (
              <pre className="text-sm text-text-primary whitespace-pre-wrap font-mono bg-black/30 p-4 rounded-lg border border-amber-500/30 overflow-x-auto">
                {JSON.stringify(rawChainState, null, 2)}
              </pre>
            ) : (
              <div className="text-text-secondary text-center py-8">
                No raw chain state data available
              </div>
            )}
          </div>
        )}

        {/* AI Chain State Tab */}
        {activeTab === 'ai_chain_state' && !loading && (
          <div className="overflow-y-auto flex-1">
            <div className="text-xs text-cyan-400 mb-2 px-1">
              What the AI sees when it calls get_system_state (with enhancements/fixes applied)
            </div>
            {aiChainState ? (
              <pre className="text-sm text-text-primary whitespace-pre-wrap font-mono bg-black/30 p-4 rounded-lg border border-cyan-500/30 overflow-x-auto">
                {JSON.stringify(aiChainState, null, 2)}
              </pre>
            ) : (
              <div className="text-text-secondary text-center py-8">
                No AI chain state data available
              </div>
            )}
          </div>
        )}

        {/* Formatted Chain State Tab */}
        {activeTab === 'formatted_chain_state' && !loading && (
          <div className="overflow-y-auto flex-1 space-y-4">
            <div className="text-xs text-emerald-400 mb-2 px-1">
              Human-readable view of chain_state data
            </div>
            {rawChainState ? (
              <div className="space-y-4">
                {/* Version & Qube ID Header */}
                <div className="p-4 bg-glass-bg rounded-lg border border-emerald-500/30">
                  <div className="flex items-center gap-4">
                    <div>
                      <span className="text-text-tertiary text-xs">Version</span>
                      <div className="text-emerald-400 font-mono">{(rawChainState as any).version || '?'}</div>
                    </div>
                    <div>
                      <span className="text-text-tertiary text-xs">Qube ID</span>
                      <div className="text-emerald-400 font-mono">{(rawChainState as any).qube_id || '?'}</div>
                    </div>
                    <div>
                      <span className="text-text-tertiary text-xs">Last Updated</span>
                      <div className="text-emerald-400">{formatTimestamp((rawChainState as any).last_updated)}</div>
                    </div>
                  </div>
                </div>

                {/* Dynamic Sections */}
                {Object.entries(rawChainState).map(([key, value]) => {
                  if (['version', 'qube_id', 'last_updated'].includes(key)) return null;
                  if (value === null || value === undefined) return null;

                  const config = sectionConfig[key] || { icon: '📄', color: 'gray', label: key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) };

                  return (
                    <div key={key} className={`p-4 bg-glass-bg rounded-lg border border-${config.color}-500/30`}>
                      <h3 className={`text-lg font-medium text-${config.color}-400 mb-3 flex items-center gap-2`}>
                        <span>{config.icon}</span>
                        {config.label}
                      </h3>

                      {typeof value === 'object' && value !== null ? (
                        <div className="grid gap-2">
                          {Object.entries(value as Record<string, unknown>).map(([subKey, subValue]) => {
                            // Format the value based on type
                            let displayValue: React.ReactNode;

                            if (subValue === null || subValue === undefined) {
                              displayValue = <span className="text-text-tertiary italic">not set</span>;
                            } else if (typeof subValue === 'boolean') {
                              displayValue = (
                                <span className={subValue ? 'text-green-400' : 'text-red-400'}>
                                  {subValue ? 'Yes' : 'No'}
                                </span>
                              );
                            } else if (typeof subValue === 'number') {
                              // Check if it looks like a timestamp
                              if (subKey.includes('timestamp') || subKey.includes('_at') || subKey === 'last_sync') {
                                displayValue = <span className="text-amber-300">{formatTimestamp(subValue)}</span>;
                              } else if (subKey.includes('satoshi') || subKey.includes('sats') || subKey === 'balance_satoshis') {
                                displayValue = <span className="text-green-400">{formatBCH(subValue)}</span>;
                              } else {
                                displayValue = <span className="text-cyan-400">{subValue.toLocaleString()}</span>;
                              }
                            } else if (Array.isArray(subValue)) {
                              if (subValue.length === 0) {
                                displayValue = <span className="text-text-tertiary italic">empty</span>;
                              } else if (subValue.length <= 3) {
                                displayValue = <span className="text-purple-400">{JSON.stringify(subValue)}</span>;
                              } else {
                                displayValue = <span className="text-purple-400">{subValue.length} items</span>;
                              }
                            } else if (typeof subValue === 'object') {
                              const objKeys = Object.keys(subValue as object);
                              if (objKeys.length === 0) {
                                displayValue = <span className="text-text-tertiary italic">empty</span>;
                              } else {
                                displayValue = (
                                  <details className="inline">
                                    <summary className="text-blue-400 cursor-pointer">{objKeys.length} fields</summary>
                                    <pre className="text-xs text-text-secondary mt-1 ml-4 font-mono">
                                      {JSON.stringify(subValue, null, 2)}
                                    </pre>
                                  </details>
                                );
                              }
                            } else {
                              displayValue = <span className="text-text-primary">{String(subValue)}</span>;
                            }

                            return (
                              <div key={subKey} className="flex items-start gap-2 py-1 border-b border-glass-border/30 last:border-0">
                                <span className="text-text-tertiary text-sm min-w-[140px]">
                                  {subKey.replace(/_/g, ' ')}:
                                </span>
                                <span className="text-sm flex-1">{displayValue}</span>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <div className="text-text-primary">{String(value)}</div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-text-secondary text-center py-8">
                No chain state data available
              </div>
            )}
          </div>
        )}

        {/* Prompt Tab */}
        {activeTab === 'prompt' && promptInfo && !loading && (
          <div className="overflow-y-auto flex-1 space-y-4">
            {/* Header info */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-glass-bg rounded-lg border border-glass-border">
              <div>
                <div className="text-xs text-text-tertiary">Qube</div>
                <div className="text-text-primary font-medium">{promptInfo.qube_name}</div>
              </div>
              <div>
                <div className="text-xs text-text-tertiary">Model</div>
                <div className="text-text-primary font-medium">{promptInfo.model}</div>
              </div>
              <div>
                <div className="text-xs text-text-tertiary">Provider</div>
                <div className="text-text-primary font-medium">{promptInfo.provider}</div>
              </div>
              <div>
                <div className="text-xs text-text-tertiary">Timestamp</div>
                <div className="text-text-primary font-medium text-sm">
                  {new Date(promptInfo.timestamp).toLocaleString()}
                </div>
              </div>
            </div>

            {/* Token counts */}
            <div className="flex gap-4 p-4 bg-glass-bg rounded-lg border border-glass-border">
              <div className="flex-1 text-center">
                <div className="text-xs text-text-tertiary">Input Tokens</div>
                <div className="text-xl text-accent-primary font-bold">
                  {formatTokens(promptInfo.input_tokens)}
                </div>
              </div>
              <div className="flex-1 text-center">
                <div className="text-xs text-text-tertiary">Output Tokens</div>
                <div className="text-xl text-accent-secondary font-bold">
                  {formatTokens(promptInfo.output_tokens)}
                </div>
              </div>
              <div className="flex-1 text-center">
                <div className="text-xs text-text-tertiary">Total Tokens</div>
                <div className="text-xl text-text-primary font-bold">
                  {formatTokens(promptInfo.total_tokens)}
                </div>
              </div>
            </div>

            {/* Messages */}
            <div className="space-y-2">
              <h3 className="text-lg font-medium text-text-primary">
                Messages ({promptInfo.messages.length})
              </h3>
              {promptInfo.messages.map((msg, index) => (
                <div
                  key={index}
                  className="border border-glass-border rounded-lg overflow-hidden"
                >
                  <button
                    onClick={() => toggleMessage(index)}
                    className="w-full p-3 bg-glass-bg hover:bg-glass-bg-hover flex justify-between items-center text-left"
                  >
                    <div className="flex items-center gap-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        msg.role === 'system' ? 'bg-purple-500/20 text-purple-300' :
                        msg.role === 'assistant' ? 'bg-green-500/20 text-green-300' :
                        msg.role === 'user' ? 'bg-blue-500/20 text-blue-300' :
                        msg.role === 'tool' ? 'bg-orange-500/20 text-orange-300' :
                        'bg-gray-500/20 text-gray-300'
                      }`}>
                        {msg.role}
                      </span>
                      <span className="text-text-secondary text-sm truncate max-w-md">
                        {msg.content?.slice(0, 100)}...
                      </span>
                    </div>
                    <span className="text-text-tertiary text-sm">
                      {expandedMessages.has(index) ? '▼' : '▶'}
                    </span>
                  </button>
                  {expandedMessages.has(index) && (
                    <div className="p-4 bg-black/20 border-t border-glass-border">
                      <pre className="text-sm text-text-primary whitespace-pre-wrap font-mono overflow-x-auto">
                        {msg.content}
                      </pre>
                      {msg.tool_calls && (
                        <div className="mt-4 pt-4 border-t border-glass-border">
                          <div className="text-xs text-text-tertiary mb-2">Tool Calls:</div>
                          <pre className="text-sm text-orange-300 whitespace-pre-wrap font-mono">
                            {JSON.stringify(msg.tool_calls, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Response preview */}
            {promptInfo.response && (
              <div className="space-y-2">
                <h3 className="text-lg font-medium text-text-primary">Response Preview</h3>
                <div className="p-4 bg-glass-bg rounded-lg border border-glass-border">
                  <pre className="text-sm text-text-secondary whitespace-pre-wrap font-mono">
                    {promptInfo.response}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}
      </GlassCard>
    </div>
  );
};
