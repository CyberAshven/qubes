import React, { useState } from 'react';
import { GlassCard } from '../glass';

interface BlockPreview {
  block_number: number;
  block_type: string;
  timestamp?: number;
  preview: string;
  relevance_score?: number;
  is_summary?: boolean;
}

interface ShortTermMemoryData {
  semantic_recalls: {
    count: number;
    blocks: BlockPreview[];
  };
  recent_permanent: {
    count: number;
    blocks: BlockPreview[];
  };
  session: {
    count: number;
    blocks: BlockPreview[];
  };
}

interface ShortTermMemoryPanelProps {
  data: ShortTermMemoryData | null;
  loading?: boolean;
  favoriteColor?: string;
}

// Helper function to format timestamp
const formatTimestamp = (timestamp: number): string => {
  if (!timestamp) return '';
  // Handle both seconds and milliseconds timestamps
  const ts = timestamp > 1e12 ? timestamp : timestamp * 1000;
  const date = new Date(ts);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);

  if (diffHours < 1) {
    const diffMins = Math.floor(diffMs / (1000 * 60));
    return `${diffMins}m ago`;
  } else if (diffHours < 24) {
    return `${Math.floor(diffHours)}h ago`;
  } else {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }
};

// Unified color scheme for block types (same as BlocksTab)
// Active types: GENESIS, MESSAGE, ACTION, SUMMARY, GAME
const BLOCK_TYPE_COLORS: Record<string, { text: string; bg: string; border: string }> = {
  'GENESIS': { text: 'text-red-500', bg: 'bg-red-500/20', border: 'border-l-red-500' },
  'MESSAGE': { text: 'text-emerald-400', bg: 'bg-emerald-400/20', border: 'border-l-emerald-400' },
  'ACTION': { text: 'text-amber-400', bg: 'bg-amber-400/20', border: 'border-l-amber-400' },
  'SUMMARY': { text: 'text-fuchsia-400', bg: 'bg-fuchsia-400/20', border: 'border-l-fuchsia-400' },
  'GAME': { text: 'text-yellow-400', bg: 'bg-yellow-400/20', border: 'border-l-yellow-400' },
};

// Section colors (where memory came from, not what type it is)
const SECTION_COLORS = {
  recalled: { text: 'text-violet-400', bg: 'bg-violet-400/20', border: 'border-l-violet-400' },
  recent: { text: 'text-slate-400', bg: 'bg-slate-400/20', border: 'border-l-slate-400' },
  session: { text: 'text-sky-400', bg: 'bg-sky-400/20', border: 'border-sky-400' },
};

// Helper function to get block type color (for badge styling)
const getBlockTypeColor = (blockType: string): string => {
  const colors = BLOCK_TYPE_COLORS[blockType];
  if (colors) {
    return `${colors.text} ${colors.bg}`;
  }
  return 'text-text-secondary bg-text-secondary/20';
};

// Helper function to get border color for block type
const getBlockTypeBorder = (blockType: string): string => {
  const colors = BLOCK_TYPE_COLORS[blockType];
  return colors?.border || 'border-l-text-secondary';
};

// Helper function to get relevance color
const getRelevanceColor = (score: number): string => {
  if (score >= 0.8) return 'text-emerald-400';
  if (score >= 0.6) return 'text-accent-primary';
  if (score >= 0.4) return 'text-yellow-400';
  return 'text-text-tertiary';
};

export const ShortTermMemoryPanel: React.FC<ShortTermMemoryPanelProps> = ({
  data,
  loading = false,
  favoriteColor = '#00ff88'
}) => {
  const [semanticExpanded, setSemanticExpanded] = useState(true);
  const [recentExpanded, setRecentExpanded] = useState(false);
  const [sessionExpanded, setSessionExpanded] = useState(false);

  if (loading) {
    return (
      <GlassCard className="p-4 mb-4">
        <div className="flex items-center gap-2">
          <div className="animate-spin w-4 h-4 border-2 border-accent-warning border-t-transparent rounded-full" />
          <span className="text-text-secondary text-sm">Loading memory...</span>
        </div>
      </GlassCard>
    );
  }

  if (!data) {
    return null;
  }

  const totalBlocks = data.semantic_recalls.count + data.recent_permanent.count + data.session.count;

  const BlockItem: React.FC<{ block: BlockPreview; showRelevance?: boolean }> = ({ block, showRelevance = false }) => (
    <div className={`p-2 bg-glass-bg/20 rounded text-xs mb-1 hover:bg-glass-bg/30 transition-colors border-l-2 ${getBlockTypeBorder(block.block_type)}`}>
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <span className={`px-1.5 py-0.5 rounded text-[10px] ${getBlockTypeColor(block.block_type)}`}>
            {block.block_type}
          </span>
          <span className="text-text-tertiary">#{block.block_number}</span>
        </div>
        <div className="flex items-center gap-2">
          {showRelevance && block.relevance_score !== undefined && (
            <span className={`${getRelevanceColor(block.relevance_score)}`}>
              {Math.round(block.relevance_score * 100)}%
            </span>
          )}
          {block.timestamp && (
            <span className="text-text-tertiary text-[10px]">
              {formatTimestamp(block.timestamp)}
            </span>
          )}
        </div>
      </div>
      <p className="text-text-secondary truncate">{block.preview}</p>
    </div>
  );

  return (
    <GlassCard className="p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-display text-text-primary flex items-center gap-2">
          <span className="text-lg">🧠</span>
          Short-Term Memory
        </h3>
        <span className="text-xs text-text-tertiary bg-glass-bg/50 px-2 py-0.5 rounded">
          {totalBlocks} blocks in context
        </span>
      </div>

      {/* Semantic Recalls */}
      <div className="mb-2">
        <button
          onClick={() => setSemanticExpanded(!semanticExpanded)}
          className="w-full flex items-center justify-between p-2 rounded hover:bg-glass-bg/30 transition-colors"
        >
          <span className={`text-sm flex items-center gap-2 ${SECTION_COLORS.recalled.text}`}>
            <span>🔮</span>
            Recalled Memories
            <span className={`text-xs ${SECTION_COLORS.recalled.bg} ${SECTION_COLORS.recalled.text} px-1.5 py-0.5 rounded`}>
              {data.semantic_recalls.count}
            </span>
          </span>
          <span className="text-xs text-text-tertiary">{semanticExpanded ? '▼' : '▶'}</span>
        </button>
        {semanticExpanded && (
          <div className="ml-4 mt-2">
            {data.semantic_recalls.blocks.length > 0 ? (
              data.semantic_recalls.blocks.map((block, idx) => (
                <BlockItem key={idx} block={block} showRelevance={true} />
              ))
            ) : (
              <div className="text-xs text-text-tertiary p-2 bg-glass-bg/10 rounded italic">
                No relevant memories found for current context
              </div>
            )}
          </div>
        )}
      </div>

      {/* Recent Permanent Blocks */}
      <div className="mb-2">
        <button
          onClick={() => setRecentExpanded(!recentExpanded)}
          className="w-full flex items-center justify-between p-2 rounded hover:bg-glass-bg/30 transition-colors"
        >
          <span className={`text-sm flex items-center gap-2 ${SECTION_COLORS.recent.text}`}>
            <span>📚</span>
            Recent History
            <span className={`text-xs ${SECTION_COLORS.recent.bg} ${SECTION_COLORS.recent.text} px-1.5 py-0.5 rounded`}>
              {data.recent_permanent.count}
            </span>
          </span>
          <span className="text-xs text-text-tertiary">{recentExpanded ? '▼' : '▶'}</span>
        </button>
        {recentExpanded && (
          <div className="ml-4 mt-2">
            {data.recent_permanent.blocks.length > 0 ? (
              data.recent_permanent.blocks.map((block, idx) => (
                <BlockItem key={idx} block={block} />
              ))
            ) : (
              <span className="text-xs text-text-tertiary">No recent blocks</span>
            )}
          </div>
        )}
      </div>

      {/* Session Blocks */}
      <div>
        <button
          onClick={() => setSessionExpanded(!sessionExpanded)}
          className="w-full flex items-center justify-between p-2 rounded hover:bg-glass-bg/30 transition-colors"
        >
          <span className={`text-sm flex items-center gap-2 ${SECTION_COLORS.session.text}`}>
            <span>⚡</span>
            Current Session
            <span className={`text-xs ${SECTION_COLORS.session.bg} ${SECTION_COLORS.session.text} px-1.5 py-0.5 rounded`}>
              {data.session.count}
            </span>
          </span>
          <span className="text-xs text-text-tertiary">{sessionExpanded ? '▼' : '▶'}</span>
        </button>
        {sessionExpanded && (
          <div className="ml-4 mt-2">
            {data.session.blocks.length > 0 ? (
              data.session.blocks.map((block, idx) => (
                <BlockItem key={idx} block={block} />
              ))
            ) : (
              <span className="text-xs text-text-tertiary">No session blocks yet</span>
            )}
          </div>
        )}
      </div>
    </GlassCard>
  );
};
