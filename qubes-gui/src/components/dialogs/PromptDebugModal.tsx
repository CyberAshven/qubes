import React, { useState, useEffect, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { GlassCard, GlassButton } from '../glass';
import { useQubeSelection } from '../../hooks/useQubeSelection';

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

interface PromptDebugModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PromptDebugModal: React.FC<PromptDebugModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [promptInfo, setPromptInfo] = useState<DebugPromptInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [expandedMessages, setExpandedMessages] = useState<Set<number>>(new Set());
  const { activeQubeByTab, currentTab } = useQubeSelection();
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

  useEffect(() => {
    if (isOpen && selectedQubeId) {
      fetchPrompt();
    }
  }, [isOpen, selectedQubeId, fetchPrompt]);

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
    if (!promptInfo) return;
    const text = JSON.stringify(promptInfo, null, 2);
    await navigator.clipboard.writeText(text);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <GlassCard className="w-full max-w-4xl max-h-[90vh] p-6 m-4 overflow-hidden flex flex-col">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-display text-accent-primary">
            AI Prompt Debug
          </h2>
          <div className="flex gap-2">
            <GlassButton
              variant="secondary"
              onClick={fetchPrompt}
              disabled={loading}
            >
              Refresh
            </GlassButton>
            <GlassButton
              variant="secondary"
              onClick={copyToClipboard}
              disabled={!promptInfo}
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

        {loading && (
          <div className="text-text-secondary text-center py-8">Loading...</div>
        )}

        {error && (
          <div className="text-red-400 text-center py-8">{error}</div>
        )}

        {promptInfo && !loading && (
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
