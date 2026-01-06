import React, { memo } from 'react';
import { GlassCard } from '../glass';

interface BlockContentViewerProps {
  blockType: string;
  content: any;
}

// Memoize the main component to prevent unnecessary re-renders
export const BlockContentViewer: React.FC<BlockContentViewerProps> = memo(({ blockType, content }) => {
  // Wrap everything in a try-catch to prevent UI crashes
  try {
    // Check if content is empty or null
    if (!content || (typeof content === 'object' && Object.keys(content).length === 0)) {
      return (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
          <div className="text-red-400 font-medium mb-2">⚠️ No Content Available</div>
          <div className="text-sm text-text-secondary">
            This block appears to be empty or failed to load. Content: {JSON.stringify(content)}
          </div>
        </div>
      );
    }

    // Check if content is still encrypted (has ciphertext field)
    if (content.ciphertext && content.nonce) {
      return (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
          <div className="text-yellow-400 font-medium mb-2">🔒 Content Still Encrypted</div>
          <div className="text-sm text-text-secondary mb-3">
            This block's content is encrypted and could not be decrypted. This may be due to:
          </div>
          <ul className="text-sm text-text-secondary list-disc list-inside space-y-1">
            <li>Incorrect password provided</li>
            <li>Decryption failed on the backend</li>
            <li>Missing master key</li>
          </ul>
          <details className="mt-3">
            <summary className="text-xs text-text-tertiary cursor-pointer">Show encrypted data</summary>
            <pre className="text-xs text-text-tertiary mt-2 p-2 bg-bg-tertiary rounded overflow-x-auto">
              {JSON.stringify(content, null, 2)}
            </pre>
          </details>
        </div>
      );
    }

    // Check if content has an error field (decryption error from backend)
    if (content.error) {
      return (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
          <div className="text-red-400 font-medium mb-2">❌ Decryption Error</div>
          <div className="text-sm text-text-secondary">
            {content.error}
          </div>
        </div>
      );
    }

    // Render based on block type
    switch (blockType) {
      case 'MESSAGE':
        return <MessageBlockContent content={content} />;
      case 'THOUGHT':
        return <ThoughtBlockContent content={content} />;
      case 'ACTION':
        return <ActionBlockContent content={content} />;
      case 'OBSERVATION':
        return <ObservationBlockContent content={content} />;
      case 'DECISION':
        return <DecisionBlockContent content={content} />;
      case 'GENESIS':
        return <GenesisBlockContent content={content} />;
      case 'SUMMARY':
        return <SummaryBlockContent content={content} />;
      case 'GAME':
        return <GameBlockContent content={content} />;
      case 'MEMORY_ANCHOR':
      case 'COLLABORATIVE_MEMORY':
      default:
        return <DefaultBlockContent content={content} />;
    }
  } catch (error) {
    // Catch any rendering errors to prevent UI crash
    console.error('BlockContentViewer rendering error:', error);
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
        <div className="text-red-400 font-medium mb-2">❌ Rendering Error</div>
        <div className="text-sm text-text-secondary mb-2">
          Failed to render block content: {error instanceof Error ? error.message : String(error)}
        </div>
        <details className="mt-3">
          <summary className="text-xs text-text-tertiary cursor-pointer">Show raw content</summary>
          <pre className="text-xs text-text-tertiary mt-2 p-2 bg-bg-tertiary rounded overflow-x-auto">
            {JSON.stringify(content, null, 2)}
          </pre>
        </details>
      </div>
    );
  }
});

// Memoize all sub-components for better performance
const MessageBlockContent: React.FC<{ content: any }> = memo(({ content }) => {
  // Handle both permanent and session MESSAGE blocks
  // Session blocks: { message_type, message_body, recipient_id, ... }
  // Permanent blocks: { user_message, response, ... }
  const userMessage = content.message_body || content.user_message || content.message || '';
  const qubeResponse = content.response || content.qube_response || '';
  const messageType = content.message_type || '';

  return (
    <div className="space-y-4">
      {/* User Message */}
      {userMessage && (
        <div className="border-l-4 border-accent-primary pl-4">
          <div className="text-xs text-text-tertiary mb-1 font-medium">
            {messageType === 'human_to_qube' ? 'User' : 'Message'}
          </div>
          <div className="text-text-primary whitespace-pre-wrap">{userMessage}</div>
        </div>
      )}

      {/* Qube Response */}
      {qubeResponse && (
        <div className="border-l-4 border-accent-success pl-4">
          <div className="text-xs text-text-tertiary mb-1 font-medium">Qube</div>
          <div className="text-text-primary whitespace-pre-wrap">{qubeResponse}</div>
        </div>
      )}

      {/* Message metadata for session blocks */}
      {messageType && (
        <div className="text-xs text-text-tertiary mt-2">
          Type: {messageType}
          {content.conversation_id && ` | Conversation: ${content.conversation_id}`}
        </div>
      )}
    </div>
  );
});

const ThoughtBlockContent: React.FC<{ content: any }> = memo(({ content }) => {
  const thought = content.thought || content.internal_monologue || content.content || '';
  const reasoning = content.reasoning_chain || [];
  const confidence = content.confidence || null;

  return (
    <div className="bg-accent-primary/5 border border-accent-primary/20 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">💭</span>
        <span className="text-sm font-medium text-accent-primary">Internal Thought</span>
        {confidence !== null && (
          <span className="text-xs text-text-tertiary ml-auto">
            Confidence: {(confidence * 100).toFixed(0)}%
          </span>
        )}
      </div>
      <div className="text-text-primary whitespace-pre-wrap italic">{thought}</div>

      {reasoning.length > 0 && (
        <div className="mt-3 pt-3 border-t border-accent-primary/20">
          <div className="text-xs text-text-tertiary mb-2">Reasoning Chain:</div>
          <ol className="list-decimal list-inside space-y-1 text-sm text-text-primary">
            {reasoning.map((step: string, idx: number) => (
              <li key={idx}>{step}</li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
});

const ActionBlockContent: React.FC<{ content: any }> = memo(({ content }) => {
  // Defensive: ensure content is an object
  if (!content || typeof content !== 'object') {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
        <div className="text-red-400 font-medium mb-2">⚠️ Invalid ACTION Block</div>
        <div className="text-sm text-text-secondary">
          Content is not an object: {JSON.stringify(content)}
        </div>
      </div>
    );
  }

  // Handle various ACTION block formats
  const actionType = content.action_type || content.type || 'Unknown';
  const result = content.result || content.observation || null;
  const cost = content.cost_estimate || content.cost || null;

  // Check if result is a web search result (has query, results, success fields)
  const isWebSearchResult = result && typeof result === 'object' && 'query' in result;

  // For web search, show query in the action section
  const actionDescription = isWebSearchResult
    ? `Search query: "${result.query || 'N/A'}"`
    : (content.action || content.action_description || 'Action executed');

  return (
    <div className="space-y-3">
      <div className="bg-accent-warning/5 border border-accent-warning/20 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-lg">⚡</span>
          <span className="text-sm font-medium text-accent-warning">Action: {actionType}</span>
        </div>
        <div className="text-text-primary whitespace-pre-wrap">{actionDescription}</div>

        {cost !== null && (
          <div className="mt-2 text-xs text-text-tertiary">
            Estimated cost: ${cost}
          </div>
        )}
      </div>

      {result && (
        <div className="bg-accent-success/5 border border-accent-success/20 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">📊</span>
            <span className="text-sm font-medium text-accent-success">Result</span>
          </div>

          {isWebSearchResult ? (
            <div className="space-y-3">
              {result.results && Array.isArray(result.results) && result.results.length > 0 ? (
                <div className="space-y-2">
                  {result.results.map((item: any, idx: number) => {
                    // Defensive: ensure item is an object
                    if (!item || typeof item !== 'object') {
                      return (
                        <div key={idx} className="bg-bg-tertiary p-4 rounded border-l-2 border-red-500">
                          <div className="text-xs text-red-400">Invalid result item: {JSON.stringify(item)}</div>
                        </div>
                      );
                    }

                    return (
                      <div key={idx} className="bg-bg-tertiary p-4 rounded border-l-2 border-accent-primary">
                        {/* Handle Perplexity-style results (content + source) */}
                        {item.content && (
                          <div className="text-sm text-text-primary whitespace-pre-wrap mb-2">
                            {String(item.content)}
                          </div>
                        )}
                        {item.source && (
                          <div className="text-xs text-text-tertiary">
                            Source: {String(item.source)}
                          </div>
                        )}

                        {/* Handle traditional search results (title, url, snippet) */}
                        {item.title && (
                          <div className="font-medium text-text-primary mb-1">{String(item.title)}</div>
                        )}
                        {item.url && (
                          <a
                            href={String(item.url)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-accent-primary hover:underline mb-1 block break-all"
                          >
                            {String(item.url)}
                          </a>
                        )}
                        {item.snippet && !item.content && (
                          <div className="text-sm text-text-secondary mt-2">{String(item.snippet)}</div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-sm text-text-secondary italic">
                  Search completed but no results were returned.
                  {result.success !== undefined && (
                    <div className="mt-2 text-xs">
                      Status: {result.success ? '✅ Success' : '❌ Failed'}
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="text-text-primary whitespace-pre-wrap">
              {typeof result === 'string' ? result : JSON.stringify(result, null, 2)}
            </div>
          )}
        </div>
      )}
    </div>
  );
});

const ObservationBlockContent: React.FC<{ content: any }> = memo(({ content }) => {
  const source = content.observation_source || content.source || 'Unknown';
  const data = content.observation_data || content.data || content.observation || '';
  const relatedAction = content.related_action_block || null;
  const reliability = content.reliability_score || null;

  return (
    <div className="bg-blue-500/5 border border-blue-500/20 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">👁️</span>
        <span className="text-sm font-medium text-blue-400">Observation from {source}</span>
        {reliability !== null && (
          <span className="text-xs text-text-tertiary ml-auto">
            Reliability: {(reliability * 100).toFixed(0)}%
          </span>
        )}
      </div>
      <div className="text-text-primary whitespace-pre-wrap">{data}</div>

      {relatedAction !== null && (
        <div className="mt-2 text-xs text-text-tertiary">
          Related to Action Block #{relatedAction}
        </div>
      )}
    </div>
  );
});

const DecisionBlockContent: React.FC<{ content: any }> = memo(({ content }) => {
  const decision = content.decision || 'Unknown';
  const fromValue = content.from_value || null;
  const toValue = content.to_value || null;
  const reasoning = content.reasoning || '';
  const impact = content.impact_assessment || null;

  return (
    <div className="bg-pink-500/5 border border-pink-500/20 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">⚖️</span>
        <span className="text-sm font-medium text-pink-400">Decision: {decision}</span>
      </div>

      {fromValue && toValue && (
        <div className="text-sm text-text-secondary mb-2">
          Changed from <span className="font-mono text-accent-warning">{fromValue}</span> to{' '}
          <span className="font-mono text-accent-success">{toValue}</span>
        </div>
      )}

      {reasoning && (
        <div className="mt-3">
          <div className="text-xs text-text-tertiary mb-1">Reasoning:</div>
          <div className="text-text-primary whitespace-pre-wrap">{reasoning}</div>
        </div>
      )}

      {impact && (
        <div className="mt-2 text-xs text-text-tertiary">
          Impact: <span className="capitalize">{impact}</span>
        </div>
      )}
    </div>
  );
});

const GenesisBlockContent: React.FC<{ content: any }> = memo(({ content }) => {
  return (
    <div className="space-y-4">
      <div className="bg-accent-primary/5 border border-accent-primary/20 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-lg">🌟</span>
          <span className="text-sm font-medium text-accent-primary">Genesis Block</span>
        </div>

        <div className="space-y-3 text-sm">
          {content.qube_name && (
            <div>
              <span className="text-text-tertiary">Name:</span>
              <div className="text-text-primary font-medium mt-1">{content.qube_name}</div>
            </div>
          )}

          {content.genesis_prompt && (
            <div>
              <span className="text-text-tertiary">Genesis Prompt:</span>
              <div className="text-text-primary mt-1 whitespace-pre-wrap bg-bg-tertiary p-3 rounded">
                {content.genesis_prompt}
              </div>
            </div>
          )}

          {content.ai_model && (
            <div>
              <span className="text-text-tertiary">AI Model:</span>
              <div className="text-text-primary font-mono mt-1">{content.ai_model}</div>
            </div>
          )}

          {content.birth_timestamp && (
            <div>
              <span className="text-text-tertiary">Birth:</span>
              <div className="text-text-primary mt-1">
                {new Date(content.birth_timestamp * 1000).toLocaleString()}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

const SummaryBlockContent: React.FC<{ content: any }> = memo(({ content }) => {
  const summary = content.summary_text || content.summary || content.content || '';
  const keyPoints = content.key_points || content.key_insights || [];
  const summarizedBlocks = content.summarized_blocks || [];
  const blockCount = content.block_count || summarizedBlocks.length || 0;
  const sessionId = content.session_id || null;
  const summaryType = content.summary_type || 'unknown';

  // Format block range for display
  const getBlockRange = () => {
    if (summarizedBlocks.length === 0) return 'Unknown';
    const min = Math.min(...summarizedBlocks);
    const max = Math.max(...summarizedBlocks);
    if (min === max) return `Block #${min}`;
    return `Blocks #${min}-${max}`;
  };

  return (
    <div className="bg-accent-success/5 border border-accent-success/20 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">📝</span>
        <span className="text-sm font-medium text-accent-success">Summary</span>
        {summaryType && (
          <span className="text-xs text-text-tertiary ml-auto capitalize">
            {summaryType.replace('_', ' ')}
          </span>
        )}
      </div>

      {/* Summary metadata */}
      <div className="bg-bg-tertiary/50 rounded-lg p-3 mb-3 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-text-tertiary">Covers:</span>
          <span className="text-accent-primary font-medium">{getBlockRange()}</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-text-tertiary">Block Count:</span>
          <span className="text-text-primary font-medium">{blockCount}</span>
        </div>
        {sessionId && (
          <div className="flex items-center justify-between text-xs">
            <span className="text-text-tertiary">Session:</span>
            <span className="text-text-primary font-mono text-[10px]">{sessionId}</span>
          </div>
        )}
        {summarizedBlocks.length > 0 && (
          <details className="mt-2">
            <summary className="text-xs text-text-tertiary cursor-pointer hover:text-accent-success">
              Show all block numbers ({summarizedBlocks.length})
            </summary>
            <div className="mt-2 p-2 bg-bg-tertiary rounded text-xs text-text-primary font-mono max-h-32 overflow-y-auto">
              {summarizedBlocks.join(', ')}
            </div>
          </details>
        )}
      </div>

      {/* Summary text */}
      <div className="text-text-primary whitespace-pre-wrap mb-3">{summary}</div>

      {/* Key points */}
      {keyPoints.length > 0 && (
        <div className="mt-3 pt-3 border-t border-accent-success/20">
          <div className="text-xs text-text-tertiary mb-2 font-medium">Key Points:</div>
          <ul className="list-disc list-inside space-y-1 text-sm text-text-primary">
            {keyPoints.map((point: string, idx: number) => (
              <li key={idx}>{point}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
});

const GameBlockContent: React.FC<{ content: any }> = memo(({ content }) => {
  const gameType = content.game_type || 'unknown';
  const whitePlayer = content.white_player || { id: 'Unknown', type: 'unknown' };
  const blackPlayer = content.black_player || { id: 'Unknown', type: 'unknown' };
  const result = content.result || '?';
  const termination = content.termination || 'unknown';
  const totalMoves = content.total_moves || 0;
  const durationSeconds = content.duration_seconds || 0;
  const xpEarned = content.xp_earned || 0;
  const pgn = content.pgn || '';
  const chatLog = content.chat_log || [];

  // Format duration as hours:minutes:seconds
  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    }
    return `${secs}s`;
  };

  // Get result description
  const getResultDescription = () => {
    if (result === '1-0') return `${whitePlayer.id} wins`;
    if (result === '0-1') return `${blackPlayer.id} wins`;
    if (result === '1/2-1/2') return 'Draw';
    return result;
  };

  // Get player display with icon
  const PlayerDisplay: React.FC<{ player: any; color: 'white' | 'black' }> = ({ player, color }) => {
    const isQube = player.type === 'qube';
    const isWinner = (color === 'white' && result === '1-0') || (color === 'black' && result === '0-1');

    return (
      <div className={`flex items-center gap-2 p-2 rounded ${isWinner ? 'bg-green-500/20 border border-green-500/40' : 'bg-bg-tertiary'}`}>
        <span className="text-lg">{color === 'white' ? '⬜' : '⬛'}</span>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-text-primary">{player.id}</span>
            {isQube && <span className="text-xs text-accent-primary bg-accent-primary/20 px-1.5 py-0.5 rounded">Qube</span>}
            {player.type === 'human' && <span className="text-xs text-emerald-400 bg-emerald-400/20 px-1.5 py-0.5 rounded">Human</span>}
          </div>
        </div>
        {isWinner && <span className="text-yellow-400 text-lg">👑</span>}
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Game Header */}
      <div className="bg-amber-400/10 border border-amber-400/30 rounded-lg p-4">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-3xl">♟️</span>
          <div>
            <div className="text-lg font-semibold text-amber-400 capitalize">{gameType} Game</div>
            <div className="text-sm text-text-secondary">{getResultDescription()} by {termination}</div>
          </div>
        </div>

        {/* Players */}
        <div className="space-y-2 mb-4">
          <PlayerDisplay player={whitePlayer} color="white" />
          <div className="text-center text-text-tertiary text-xs">vs</div>
          <PlayerDisplay player={blackPlayer} color="black" />
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-3 gap-3 text-center">
          <div className="bg-bg-tertiary rounded-lg p-3">
            <div className="text-2xl font-bold text-text-primary">{totalMoves}</div>
            <div className="text-xs text-text-tertiary">Moves</div>
          </div>
          <div className="bg-bg-tertiary rounded-lg p-3">
            <div className="text-2xl font-bold text-text-primary">{formatDuration(durationSeconds)}</div>
            <div className="text-xs text-text-tertiary">Duration</div>
          </div>
          <div className="bg-bg-tertiary rounded-lg p-3">
            <div className="text-2xl font-bold text-green-400">+{xpEarned}</div>
            <div className="text-xs text-text-tertiary">XP Earned</div>
          </div>
        </div>
      </div>

      {/* PGN Section */}
      {pgn && (
        <details className="bg-bg-tertiary/50 border border-glass-border rounded-lg overflow-hidden">
          <summary className="p-4 cursor-pointer hover:bg-bg-tertiary/70 transition-colors flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-lg">📋</span>
              <span className="font-medium text-text-primary">PGN Notation</span>
            </div>
            <span className="text-xs text-text-tertiary">{totalMoves} moves</span>
          </summary>
          <div className="p-4 pt-0">
            <pre className="text-xs text-text-secondary font-mono whitespace-pre-wrap bg-bg-tertiary p-3 rounded max-h-64 overflow-y-auto">
              {pgn}
            </pre>
          </div>
        </details>
      )}

      {/* Chat Log Section */}
      {chatLog.length > 0 && (
        <details className="bg-bg-tertiary/50 border border-glass-border rounded-lg overflow-hidden">
          <summary className="p-4 cursor-pointer hover:bg-bg-tertiary/70 transition-colors flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-lg">💬</span>
              <span className="font-medium text-text-primary">Game Chat</span>
            </div>
            <span className="text-xs text-text-tertiary">{chatLog.length} messages</span>
          </summary>
          <div className="p-4 pt-0 space-y-2 max-h-64 overflow-y-auto">
            {chatLog.map((msg: any, idx: number) => (
              <div key={idx} className="bg-bg-tertiary p-3 rounded-lg">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-amber-400">{msg.sender_id}</span>
                    {msg.sender_type === 'qube' && (
                      <span className="text-xs text-accent-primary bg-accent-primary/20 px-1 py-0.5 rounded">Qube</span>
                    )}
                  </div>
                  <span className="text-xs text-text-tertiary">Move {msg.move_number || '?'}</span>
                </div>
                <div className="text-sm text-text-primary">{msg.message}</div>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
});

const DefaultBlockContent: React.FC<{ content: any }> = memo(({ content }) => {
  return (
    <div className="bg-bg-tertiary rounded-lg p-4 overflow-x-auto">
      <pre className="text-xs text-text-primary font-mono">
        {JSON.stringify(content, null, 2)}
      </pre>
    </div>
  );
});
