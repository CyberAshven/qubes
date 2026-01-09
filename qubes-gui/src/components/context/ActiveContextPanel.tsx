import React, { useState } from 'react';
import { GlassCard } from '../glass';
import { formatModelName } from '../../utils/modelFormatter';

interface GenesisIdentity {
  name: string;
  qube_id: string;
  birth_date: string | null;
  genesis_prompt: string;
  favorite_color: string;
  ai_model: string;
  voice_model: string;
  creator: string;
  nft_category_id: string | null;
  mint_txid: string | null;
}

interface Relationship {
  entity_id: string;
  name: string;
  status: string;
  trust_level: number;
  interaction_count: number;
}

interface SkillInfo {
  skill_id: string;
  total_xp: number;
  unlocked: number;
  level: number;
}

interface SkillsTotals {
  total_xp: number;
  unlocked_skills: number;
  categories: number;
}

interface OwnerInfoField {
  key: string;
  value: string;
  sensitivity: 'public' | 'private' | 'secret';
}

interface OwnerInfoSummary {
  total_fields: number;
  public_fields: number;
  private_fields: number;
  secret_fields: number;
  categories_populated: number;
  top_fields: OwnerInfoField[];
}

interface WalletTransaction {
  txid: string;
  amount_sats: number;
  type: 'received' | 'sent';
  timestamp?: number;
  confirmations: number;
}

interface WalletInfo {
  p2sh_address: string;
  balance_sats?: number;
  balance_bch?: number;
  recent_transactions?: WalletTransaction[];
  has_wallet: boolean;
}

interface ActiveContextData {
  genesis_identity: GenesisIdentity;
  relationships: {
    count: number;
    top_relationships: Relationship[];
  };
  skills: {
    totals: SkillsTotals;
    top_skills: SkillInfo[];
  };
  owner_info?: OwnerInfoSummary | null;
  wallet: WalletInfo | null;
}

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
  estimated_tokens?: number;
  max_context_window?: number;
}

interface ActiveContextPanelProps {
  data: ActiveContextData | null;
  shortTermMemory?: ShortTermMemoryData | null;
  loading?: boolean;
  favoriteColor?: string;
}

// Helper function to format timestamp
const formatTimestamp = (timestamp: number): string => {
  if (!timestamp) return '';
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

// Helper function to get block type color
const getBlockTypeColor = (blockType: string): string => {
  const colors: Record<string, string> = {
    'GENESIS': 'text-red-500 bg-red-500/20',
    'MESSAGE': 'text-emerald-400 bg-emerald-400/20',
    'THOUGHT': 'text-purple-400 bg-purple-400/20',
    'ACTION': 'text-accent-warning bg-accent-warning/20',
    'SUMMARY': 'text-fuchsia-400 bg-fuchsia-400/20',
    'DECISION': 'text-pink-400 bg-pink-400/20',
    'OBSERVATION': 'text-blue-400 bg-blue-400/20',
    'MEMORY_ANCHOR': 'text-indigo-400 bg-indigo-400/20',
    'GAME': 'text-amber-400 bg-amber-400/20',
  };
  return colors[blockType] || 'text-text-secondary bg-text-secondary/20';
};

const getRelevanceColor = (score: number): string => {
  if (score >= 0.8) return 'text-emerald-400';
  if (score >= 0.6) return 'text-accent-primary';
  if (score >= 0.4) return 'text-yellow-400';
  return 'text-text-tertiary';
};

export const ActiveContextPanel: React.FC<ActiveContextPanelProps> = ({
  data,
  shortTermMemory,
  loading = false,
  favoriteColor = '#00ff88'
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [genesisExpanded, setGenesisExpanded] = useState(false);
  const [relationshipsExpanded, setRelationshipsExpanded] = useState(false);
  const [skillsExpanded, setSkillsExpanded] = useState(false);
  const [ownerInfoExpanded, setOwnerInfoExpanded] = useState(false);
  const [walletExpanded, setWalletExpanded] = useState(false);
  const [semanticExpanded, setSemanticExpanded] = useState(false);
  const [recentExpanded, setRecentExpanded] = useState(false);
  const [sessionExpanded, setSessionExpanded] = useState(false);

  if (loading) {
    return (
      <GlassCard className="p-4 mb-4">
        <div className="flex items-center gap-2">
          <div className="animate-spin w-4 h-4 border-2 border-accent-primary border-t-transparent rounded-full" />
          <span className="text-text-secondary text-sm">Loading context...</span>
        </div>
      </GlassCard>
    );
  }

  if (!data) {
    return null;
  }

  const getTrustColor = (trust: number): string => {
    if (trust >= 0.8) return 'text-emerald-400';
    if (trust >= 0.6) return 'text-accent-primary';
    if (trust >= 0.4) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getStatusEmoji = (status: string): string => {
    switch (status) {
      case 'connected': return '🤝';
      case 'pending': return '⏳';
      case 'blocked': return '🚫';
      case 'friend': return '💚';
      default: return '👤';
    }
  };

  const formatBCH = (sats: number): string => {
    if (!sats) return '0 BCH';
    const bch = sats / 100_000_000;
    if (bch < 0.0001) return `${sats} sats`;
    return `${bch.toFixed(8)} BCH`;
  };

  // Get estimated tokens and max context window from short-term memory
  const estimatedTokens = shortTermMemory?.estimated_tokens || 0;
  const maxContextWindow = shortTermMemory?.max_context_window || 128000;

  // Calculate usage percentage
  const usagePercent = maxContextWindow > 0 ? (estimatedTokens / maxContextWindow) * 100 : 0;

  // Get color based on usage percentage
  // Green: < 25%, Yellow: 25-60%, Red: > 60%
  const getTokenColor = (): { text: string; bg: string } => {
    if (usagePercent < 25) {
      return { text: 'text-emerald-400', bg: 'bg-emerald-400/20' };
    } else if (usagePercent < 60) {
      return { text: 'text-yellow-400', bg: 'bg-yellow-400/20' };
    } else {
      return { text: 'text-red-400', bg: 'bg-red-400/20' };
    }
  };

  const tokenColor = getTokenColor();

  // Format token count (e.g., 1234 -> "1.2K")
  const formatTokenCount = (tokens: number): string => {
    if (tokens >= 1000) {
      return `~${(tokens / 1000).toFixed(1)}K`;
    }
    return `~${tokens}`;
  };

  const BlockItem: React.FC<{ block: BlockPreview; showRelevance?: boolean }> = ({ block, showRelevance = false }) => (
    <div className="p-2 bg-glass-bg/20 rounded text-xs mb-1 hover:bg-glass-bg/30 transition-colors">
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
    <GlassCard className="p-3 mb-4 border-l-2" style={{ borderLeftColor: favoriteColor }}>
      {/* Collapsible Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between mb-2"
      >
        <h3 className="text-sm font-display flex items-center gap-2" style={{ color: favoriteColor }}>
          <span className="text-lg">🧬</span>
          Active Context
          {estimatedTokens > 0 && (
            <span
              className={`text-xs px-1.5 py-0.5 rounded ${tokenColor.text} ${tokenColor.bg}`}
              title={`${usagePercent.toFixed(1)}% of ${(maxContextWindow / 1000).toFixed(0)}K context window`}
            >
              {formatTokenCount(estimatedTokens)} tokens
            </span>
          )}
        </h3>
        <span className="text-xs text-text-tertiary">{isExpanded ? '▼' : '▶'}</span>
      </button>

      {isExpanded && (
        <div className="space-y-1">
          {/* Genesis Identity */}
          <div>
            <button
              onClick={() => setGenesisExpanded(!genesisExpanded)}
              className="w-full flex items-center justify-between p-2 rounded hover:bg-glass-bg/30 transition-colors"
            >
              <span className="text-sm text-text-secondary flex items-center gap-2">
                <span>🌟</span>
                Genesis Identity
              </span>
              <span className="text-xs text-text-tertiary">{genesisExpanded ? '▼' : '▶'}</span>
            </button>
            {genesisExpanded && (
              <div className="ml-6 mt-2 space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-text-tertiary">Name:</span>
                  <span className="text-text-primary">{data.genesis_identity.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-tertiary">Born:</span>
                  <span className="text-text-primary">{data.genesis_identity.birth_date || 'Unknown'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-tertiary">Model:</span>
                  <span className="text-text-primary">{formatModelName(data.genesis_identity.ai_model)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-tertiary">Creator:</span>
                  <span className="text-text-primary">{data.genesis_identity.creator}</span>
                </div>
                {data.genesis_identity.nft_category_id && (
                  <div className="flex justify-between">
                    <span className="text-text-tertiary">NFT:</span>
                    <span className="text-emerald-400">Minted ✓</span>
                  </div>
                )}
                <div className="mt-2 p-2 bg-glass-bg/30 rounded text-text-secondary">
                  {data.genesis_identity.genesis_prompt}
                </div>
              </div>
            )}
          </div>

          {/* Relationships */}
          <div>
            <button
              onClick={() => setRelationshipsExpanded(!relationshipsExpanded)}
              className="w-full flex items-center justify-between p-2 rounded hover:bg-glass-bg/30 transition-colors"
            >
              <span className="text-sm text-text-secondary flex items-center gap-2">
                <span>👥</span>
                Relationships
                <span className="text-xs bg-glass-bg/50 px-1.5 py-0.5 rounded">
                  {data.relationships.count}
                </span>
              </span>
              <span className="text-xs text-text-tertiary">{relationshipsExpanded ? '▼' : '▶'}</span>
            </button>
            {relationshipsExpanded && (
              <div className="ml-6 mt-2 space-y-2">
                {data.relationships.top_relationships.length > 0 ? (
                  data.relationships.top_relationships.map((rel, idx) => (
                    <div key={idx} className="text-xs p-1.5 bg-glass-bg/20 rounded">
                      <div className="flex items-center gap-2 mb-1">
                        <span>{getStatusEmoji(rel.status)}</span>
                        <span className="text-text-primary font-medium">{rel.name}</span>
                      </div>
                      <div className="flex items-center gap-3 ml-5 text-[11px]">
                        <span>
                          <span className="text-text-tertiary">Trust: </span>
                          <span className={getTrustColor(rel.trust_level)}>
                            {Math.round(rel.trust_level * 100)}%
                          </span>
                        </span>
                        <span>
                          <span className="text-text-tertiary">Messages: </span>
                          <span className="text-text-secondary">{rel.interaction_count}</span>
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <span className="text-xs text-text-tertiary">No relationships yet</span>
                )}
              </div>
            )}
          </div>

          {/* Skills */}
          <div>
            <button
              onClick={() => setSkillsExpanded(!skillsExpanded)}
              className="w-full flex items-center justify-between p-2 rounded hover:bg-glass-bg/30 transition-colors"
            >
              <span className="text-sm text-text-secondary flex items-center gap-2">
                <span>⚡</span>
                Skills
                <span className="text-xs bg-glass-bg/50 px-1.5 py-0.5 rounded">
                  {data.skills.totals.total_xp} XP
                </span>
              </span>
              <span className="text-xs text-text-tertiary">{skillsExpanded ? '▼' : '▶'}</span>
            </button>
            {skillsExpanded && (
              <div className="ml-6 mt-2 space-y-2">
                <div className="flex justify-between text-xs text-text-tertiary">
                  <span>Unlocked: {data.skills.totals.unlocked_skills}</span>
                  <span>Categories: {data.skills.totals.categories}</span>
                </div>
                {data.skills.top_skills.length > 0 ? (
                  data.skills.top_skills.map((skill, idx) => (
                    <div key={idx} className="flex items-center justify-between text-xs p-1.5 bg-glass-bg/20 rounded">
                      <span className="text-text-primary capitalize">
                        {skill.skill_id.replace(/_/g, ' ')}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-accent-primary">Lvl {skill.level}</span>
                        <span className="text-text-tertiary">{skill.total_xp} XP</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <span className="text-xs text-text-tertiary">No skills recorded yet</span>
                )}
              </div>
            )}
          </div>

          {/* Owner Info */}
          <div>
            <button
              onClick={() => setOwnerInfoExpanded(!ownerInfoExpanded)}
              className="w-full flex items-center justify-between p-2 rounded hover:bg-glass-bg/30 transition-colors"
            >
              <span className="text-sm text-text-secondary flex items-center gap-2">
                <span>👤</span>
                Owner Info
                {data.owner_info && data.owner_info.total_fields > 0 ? (
                  <span className="text-xs bg-glass-bg/50 px-1.5 py-0.5 rounded">
                    {data.owner_info.total_fields} fields
                  </span>
                ) : (
                  <span className="text-xs text-text-tertiary">0</span>
                )}
              </span>
              <span className="text-xs text-text-tertiary">{ownerInfoExpanded ? '▼' : '▶'}</span>
            </button>
            {ownerInfoExpanded && (
              <div className="ml-6 mt-2 space-y-2">
                {data.owner_info && data.owner_info.total_fields > 0 ? (
                  <>
                    <div className="flex justify-between text-xs text-text-tertiary">
                      <span>🌐 Public: {data.owner_info.public_fields}</span>
                      <span>🔒 Private: {data.owner_info.private_fields}</span>
                      {data.owner_info.secret_fields > 0 && (
                        <span>🔐 Secret: {data.owner_info.secret_fields}</span>
                      )}
                    </div>
                    {data.owner_info.top_fields.map((field, idx) => (
                      <div key={idx} className="flex items-center justify-between text-xs p-1.5 bg-glass-bg/20 rounded">
                        <span className="text-text-primary capitalize flex items-center gap-1">
                          <span className={field.sensitivity === 'public' ? 'text-emerald-400' : 'text-yellow-400'}>
                            {field.sensitivity === 'public' ? '🌐' : '🔒'}
                          </span>
                          {field.key.replace(/_/g, ' ')}
                        </span>
                        <span className="text-text-secondary truncate max-w-[120px]" title={field.value}>
                          {field.value}
                        </span>
                      </div>
                    ))}
                  </>
                ) : (
                  <div className="text-xs text-text-tertiary p-2 bg-glass-bg/10 rounded italic">
                    No owner info yet. Chat with your Qube and share personal details - they'll remember!
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Wallet */}
          {data.wallet && (
            <div>
              <button
                onClick={() => setWalletExpanded(!walletExpanded)}
                className="w-full flex items-center justify-between p-2 rounded hover:bg-glass-bg/30 transition-colors"
              >
                <span className="text-sm text-text-secondary flex items-center gap-2">
                  <span>💰</span>
                  Wallet
                  <span className="text-xs text-emerald-400">
                    {formatBCH(data.wallet.balance_sats || 0)}
                  </span>
                </span>
                <span className="text-xs text-text-tertiary">{walletExpanded ? '▼' : '▶'}</span>
              </button>
              {walletExpanded && (
                <div className="ml-6 mt-2 text-xs space-y-1">
                  <div className="p-2 bg-glass-bg/20 rounded">
                    <span className="text-text-tertiary">Address: </span>
                    <span className="text-text-primary font-mono text-[10px]">
                      {data.wallet.p2sh_address}
                    </span>
                  </div>
                  <div className="mt-2">
                    <span className="text-text-tertiary text-[11px]">Recent Transactions:</span>
                    {data.wallet.recent_transactions && data.wallet.recent_transactions.length > 0 ? (
                      <div className="mt-1 space-y-1">
                        {data.wallet.recent_transactions.map((tx, idx) => (
                          <div key={idx} className="flex items-center justify-between p-1.5 bg-glass-bg/20 rounded">
                            <div className="flex items-center gap-2">
                              <span className={tx.type === 'received' ? 'text-emerald-400' : 'text-red-400'}>
                                {tx.type === 'received' ? '↓' : '↑'}
                              </span>
                              <span className="text-text-tertiary font-mono text-[10px]">{tx.txid}</span>
                            </div>
                            <span className={tx.type === 'received' ? 'text-emerald-400' : 'text-red-400'}>
                              {tx.type === 'received' ? '+' : '-'}{formatBCH(Math.abs(tx.amount_sats))}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="mt-1 p-1.5 bg-glass-bg/10 rounded text-text-tertiary italic">
                        No transactions yet
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Short-Term Memory Section */}
          {shortTermMemory && (
            <>
              {/* Semantic Recalls */}
              <div>
                <button
                  onClick={() => setSemanticExpanded(!semanticExpanded)}
                  className="w-full flex items-center justify-between p-2 rounded hover:bg-glass-bg/30 transition-colors"
                >
                  <span className="text-sm text-text-secondary flex items-center gap-2">
                    <span>🔮</span>
                    Recalled Memories
                    <span className="text-xs bg-purple-500/20 text-purple-400 px-1.5 py-0.5 rounded">
                      {shortTermMemory.semantic_recalls.count}
                    </span>
                  </span>
                  <span className="text-xs text-text-tertiary">{semanticExpanded ? '▼' : '▶'}</span>
                </button>
                {semanticExpanded && (
                  <div className="ml-4 mt-2">
                    {shortTermMemory.semantic_recalls.blocks.length > 0 ? (
                      shortTermMemory.semantic_recalls.blocks.map((block, idx) => (
                        <BlockItem key={idx} block={block} showRelevance={true} />
                      ))
                    ) : (
                      <div className="text-xs text-text-tertiary p-2 bg-glass-bg/10 rounded italic">
                        No relevant memories found
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Recent History */}
              <div>
                <button
                  onClick={() => setRecentExpanded(!recentExpanded)}
                  className="w-full flex items-center justify-between p-2 rounded hover:bg-glass-bg/30 transition-colors"
                >
                  <span className="text-sm text-text-secondary flex items-center gap-2">
                    <span>📚</span>
                    Recent History
                    <span className="text-xs bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded">
                      {shortTermMemory.recent_permanent.count}
                    </span>
                  </span>
                  <span className="text-xs text-text-tertiary">{recentExpanded ? '▼' : '▶'}</span>
                </button>
                {recentExpanded && (
                  <div className="ml-4 mt-2">
                    {shortTermMemory.recent_permanent.blocks.length > 0 ? (
                      shortTermMemory.recent_permanent.blocks.map((block, idx) => (
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
                  <span className="text-sm text-text-secondary flex items-center gap-2">
                    <span>⚡</span>
                    Current Session
                    <span className="text-xs bg-accent-warning/20 text-accent-warning px-1.5 py-0.5 rounded">
                      {shortTermMemory.session.count}
                    </span>
                  </span>
                  <span className="text-xs text-text-tertiary">{sessionExpanded ? '▼' : '▶'}</span>
                </button>
                {sessionExpanded && (
                  <div className="ml-4 mt-2">
                    {shortTermMemory.session.blocks.length > 0 ? (
                      shortTermMemory.session.blocks.map((block, idx) => (
                        <BlockItem key={idx} block={block} />
                      ))
                    ) : (
                      <span className="text-xs text-text-tertiary">No session blocks yet</span>
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </GlassCard>
  );
};
