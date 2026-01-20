import React, { useState, useEffect, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { GlassCard, GlassButton } from '../glass';
import { useQubeSelection } from '../../hooks/useQubeSelection';
import { useAuth } from '../../hooks/useAuth';

// Polling interval for real-time updates (5 seconds)
const POLL_INTERVAL_MS = 5000;

interface MessagePreview {
  role: string;
  content: string;
  name?: string;
}

interface SystemPromptPreview {
  system_prompt: string;
  messages: MessagePreview[];
  model: string;
  provider: string;
  qube_name: string;
  qube_id: string;
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
  const [rawChainState, setRawChainState] = useState<Record<string, unknown> | null>(null);
  const [aiChainState, setAiChainState] = useState<Record<string, unknown> | null>(null);
  const [systemPromptPreview, setSystemPromptPreview] = useState<SystemPromptPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>('prompt');
  const [expandedMessages, setExpandedMessages] = useState<Set<number>>(new Set([0])); // System prompt expanded by default

  const toggleMessage = (index: number) => {
    setExpandedMessages(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const expandAll = () => {
    if (systemPromptPreview?.messages) {
      setExpandedMessages(new Set(systemPromptPreview.messages.map((_, i) => i)));
    }
  };

  const collapseAll = () => {
    setExpandedMessages(new Set());
  };
  const { activeQubeByTab, currentTab } = useQubeSelection();
  const { userId, password } = useAuth();
  const selectedQubeId = activeQubeByTab[currentTab];

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

  const fetchSystemPromptPreview = useCallback(async () => {
    if (!selectedQubeId || !userId || !password) {
      return;
    }

    try {
      const result = await invoke<{
        success: boolean;
        system_prompt?: string;
        messages?: MessagePreview[];
        model?: string;
        provider?: string;
        qube_name?: string;
        qube_id?: string;
        error?: string;
      }>(
        'get_system_prompt_preview',
        { userId, qubeId: selectedQubeId, password }
      );

      if (result.success && result.system_prompt) {
        setSystemPromptPreview({
          system_prompt: result.system_prompt,
          messages: result.messages || [],
          model: result.model || 'unknown',
          provider: result.provider || 'unknown',
          qube_name: result.qube_name || '',
          qube_id: result.qube_id || selectedQubeId,
        });
      }
    } catch (err) {
      console.error('Failed to fetch system prompt preview:', err);
    }
  }, [selectedQubeId, userId, password]);

  useEffect(() => {
    if (isOpen && selectedQubeId) {
      fetchChainState();
      fetchSystemPromptPreview();
    }
  }, [isOpen, selectedQubeId, fetchChainState, fetchSystemPromptPreview]);

  // Real-time updates: Event listeners + polling
  // Events that can affect the system prompt:
  // - qube-model-changed: Model was switched
  // - model-mode-changed: Revolver/locked mode changed (could trigger model changes)
  // - qube-reset: Qube state was reset
  // Polling covers: mood changes, avatar updates, relationship changes, owner info updates
  useEffect(() => {
    if (!isOpen || !selectedQubeId) return;

    const unlisteners: Array<() => void> = [];

    // Set up event listeners for immediate updates
    const setupListeners = async () => {
      // Listen for model changes
      const unlistenModelChanged = await listen<{ qubeId: string; newModel: string }>(
        'qube-model-changed',
        (event) => {
          if (event.payload.qubeId === selectedQubeId) {
            console.log('[DebugInspector] Model changed, refreshing preview...');
            fetchSystemPromptPreview();
            fetchChainState();
          }
        }
      );
      unlisteners.push(unlistenModelChanged);

      // Listen for model mode changes (revolver mode, locked mode, etc.)
      const unlistenModeChanged = await listen<{ qubeId: string }>(
        'model-mode-changed',
        (event) => {
          if (event.payload.qubeId === selectedQubeId) {
            console.log('[DebugInspector] Model mode changed, refreshing preview...');
            fetchSystemPromptPreview();
            fetchChainState();
          }
        }
      );
      unlisteners.push(unlistenModeChanged);

      // Listen for qube reset
      const unlistenReset = await listen<{ qubeId: string }>(
        'qube-reset',
        (event) => {
          if (event.payload.qubeId === selectedQubeId) {
            console.log('[DebugInspector] Qube reset, refreshing all data...');
            fetchChainState();
            fetchSystemPromptPreview();
          }
        }
      );
      unlisteners.push(unlistenReset);

      // Listen for settings changes (voice, TTS, etc.)
      const unlistenSettingsChanged = await listen<{ qubeId: string }>(
        'qube-settings-changed',
        (event) => {
          if (event.payload.qubeId === selectedQubeId) {
            console.log('[DebugInspector] Settings changed, refreshing preview...');
            fetchSystemPromptPreview();
            fetchChainState();
          }
        }
      );
      unlisteners.push(unlistenSettingsChanged);

      // Listen for mood changes
      const unlistenMoodChanged = await listen<{ qubeId: string }>(
        'qube-mood-changed',
        (event) => {
          if (event.payload.qubeId === selectedQubeId) {
            console.log('[DebugInspector] Mood changed, refreshing preview...');
            fetchSystemPromptPreview();
            fetchChainState();
          }
        }
      );
      unlisteners.push(unlistenMoodChanged);
    };

    setupListeners();

    // Set up polling as a fallback for changes that don't emit events
    const pollInterval = setInterval(() => {
      console.log('[DebugInspector] Polling for updates...');
      fetchSystemPromptPreview();
      fetchChainState();
    }, POLL_INTERVAL_MS);

    // Cleanup
    return () => {
      unlisteners.forEach((unlisten) => unlisten());
      clearInterval(pollInterval);
    };
  }, [isOpen, selectedQubeId, fetchChainState, fetchSystemPromptPreview]);

  const copyToClipboard = async () => {
    if (activeTab === 'prompt' && systemPromptPreview) {
      const text = JSON.stringify(systemPromptPreview, null, 2);
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
    if (activeTab === 'prompt') return !systemPromptPreview;
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
              onClick={() => { fetchChainState(); fetchSystemPromptPreview(); }}
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
        {activeTab === 'prompt' && !loading && (
          <div className="overflow-y-auto flex-1 space-y-4">
            {/* Real-time System Prompt Preview */}
            {systemPromptPreview ? (
              <>
                {/* Header info - real-time values */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 p-4 bg-glass-bg rounded-lg border border-green-500/30">
                  <div>
                    <div className="text-xs text-text-tertiary">Qube</div>
                    <div className="text-text-primary font-medium">{systemPromptPreview.qube_name}</div>
                  </div>
                  <div>
                    <div className="text-xs text-text-tertiary flex items-center gap-1">
                      Model
                      <span className="text-green-400 text-[10px]">(live)</span>
                    </div>
                    <div className="text-text-primary font-medium">{systemPromptPreview.model}</div>
                  </div>
                  <div>
                    <div className="text-xs text-text-tertiary flex items-center gap-1">
                      Provider
                      <span className="text-green-400 text-[10px]">(live)</span>
                    </div>
                    <div className="text-text-primary font-medium">{systemPromptPreview.provider}</div>
                  </div>
                </div>

                {/* Messages (system prompt + conversation) */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-medium text-text-primary">
                        Messages ({systemPromptPreview.messages?.length || 0})
                      </h3>
                      <span className="text-green-400 text-xs bg-green-500/10 px-2 py-0.5 rounded">Real-time Preview</span>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={expandAll}
                        className="text-xs text-text-secondary hover:text-text-primary px-2 py-1 rounded bg-glass-bg/50 hover:bg-glass-bg transition-colors"
                      >
                        Expand All
                      </button>
                      <button
                        onClick={collapseAll}
                        className="text-xs text-text-secondary hover:text-text-primary px-2 py-1 rounded bg-glass-bg/50 hover:bg-glass-bg transition-colors"
                      >
                        Collapse All
                      </button>
                    </div>
                  </div>
                  <div className="text-xs text-green-400 mb-2">
                    This is what WOULD be sent to the AI if you continued the conversation now
                  </div>
                  <div className="space-y-2">
                    {(systemPromptPreview.messages || []).map((msg, index) => {
                      const isExpanded = expandedMessages.has(index);
                      const contentPreview = msg.content.length > 100
                        ? msg.content.substring(0, 100) + '...'
                        : msg.content;

                      return (
                        <div
                          key={index}
                          className="border border-glass-border rounded-lg overflow-hidden"
                        >
                          <button
                            onClick={() => toggleMessage(index)}
                            className="w-full p-3 bg-glass-bg flex items-center gap-3 hover:bg-glass-bg/80 transition-colors text-left"
                          >
                            <span className={`transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}>
                              ▶
                            </span>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              msg.role === 'system' ? 'bg-purple-500/20 text-purple-300' :
                              msg.role === 'assistant' ? 'bg-green-500/20 text-green-300' :
                              msg.role === 'user' ? 'bg-blue-500/20 text-blue-300' :
                              msg.role === 'tool' ? 'bg-orange-500/20 text-orange-300' :
                              'bg-gray-500/20 text-gray-300'
                            }`}>
                              {msg.name || msg.role}
                            </span>
                            {msg.name && msg.name !== msg.role && (
                              <span className="text-text-tertiary text-xs">({msg.role})</span>
                            )}
                            {!isExpanded && (
                              <span className="text-text-tertiary text-xs truncate flex-1 ml-2">
                                {contentPreview}
                              </span>
                            )}
                            <span className="text-text-tertiary text-xs ml-auto">
                              {msg.content.length} chars
                            </span>
                          </button>
                          {isExpanded && (
                            <div className="p-4 bg-black/20 border-t border-glass-border">
                              <pre className="text-sm text-text-primary whitespace-pre-wrap font-mono overflow-x-auto max-h-96 overflow-y-auto">
                                {msg.content}
                              </pre>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </>
            ) : (
              <div className="text-text-secondary text-center py-8">
                Loading system prompt preview...
              </div>
            )}
          </div>
        )}
      </GlassCard>
    </div>
  );
};
