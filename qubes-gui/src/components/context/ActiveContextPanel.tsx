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

// Section types for selection
export type ContextSectionType =
  | 'owner_info'
  | 'genesis'
  | 'relationships'
  | 'skills'
  | 'wallet'
  | 'semantic_recalls'
  | 'recent_permanent'
  | 'session';

// Data passed when a section is selected
export interface ContextSectionData {
  type: ContextSectionType;
  data: any;
  title: string;
  icon: string;
}

interface ActiveContextPanelProps {
  data: ActiveContextData | null;
  shortTermMemory?: ShortTermMemoryData | null;
  loading?: boolean;
  favoriteColor?: string;
  selectedSection?: ContextSectionType | null;
  onSectionSelect?: (section: ContextSectionData | null) => void;
}

// Helper function to format BCH
const formatBCH = (sats: number): string => {
  if (!sats) return '0 BCH';
  const bch = sats / 100_000_000;
  if (bch < 0.0001) return `${sats} sats`;
  return `${bch.toFixed(8)} BCH`;
};

export const ActiveContextPanel: React.FC<ActiveContextPanelProps> = ({
  data,
  shortTermMemory,
  loading = false,
  favoriteColor = '#00ff88',
  selectedSection,
  onSectionSelect
}) => {
  // Panel is collapsed by default
  const [isExpanded, setIsExpanded] = useState(false);

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

  // Get estimated tokens and max context window from short-term memory
  const estimatedTokens = shortTermMemory?.estimated_tokens || 0;
  const maxContextWindow = shortTermMemory?.max_context_window || 128000;

  // Calculate usage percentage
  const usagePercent = maxContextWindow > 0 ? (estimatedTokens / maxContextWindow) * 100 : 0;

  // Get color based on usage percentage
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

  // Handle section click
  const handleSectionClick = (type: ContextSectionType, sectionData: any, title: string, icon: string) => {
    if (onSectionSelect) {
      // Toggle off if clicking the same section
      if (selectedSection === type) {
        onSectionSelect(null);
      } else {
        onSectionSelect({ type, data: sectionData, title, icon });
      }
    }
  };

  // Section row component
  const SectionRow: React.FC<{
    type: ContextSectionType;
    icon: string;
    title: string;
    badge?: React.ReactNode;
    sectionData: any;
  }> = ({ type, icon, title, badge, sectionData }) => {
    const isSelected = selectedSection === type;
    return (
      <button
        onClick={() => handleSectionClick(type, sectionData, title, icon)}
        className={`w-full flex items-center justify-between p-2 rounded transition-colors ${
          isSelected
            ? 'bg-accent-primary/20 border border-accent-primary/40'
            : 'hover:bg-glass-bg/30'
        }`}
      >
        <span className="text-sm text-text-secondary flex items-center gap-2">
          <span>{icon}</span>
          <span className={isSelected ? 'text-accent-primary font-medium' : ''}>{title}</span>
          {badge}
        </span>
        <span className={`text-xs ${isSelected ? 'text-accent-primary' : 'text-text-tertiary'}`}>
          {isSelected ? '◀' : '▶'}
        </span>
      </button>
    );
  };

  return (
    <GlassCard className="p-3 mb-4 border-l-2" style={{ borderLeftColor: favoriteColor }}>
      {/* Collapsible Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between"
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
      <div className="space-y-1 mt-3">
        {/* 1. Owner Info (moved to top) */}
        <SectionRow
          type="owner_info"
          icon="👤"
          title="Owner Info"
          badge={
            data.owner_info && data.owner_info.total_fields > 0 ? (
              <span className="text-xs bg-glass-bg/50 px-1.5 py-0.5 rounded">
                {data.owner_info.total_fields} fields
              </span>
            ) : (
              <span className="text-xs text-text-tertiary">0</span>
            )
          }
          sectionData={data.owner_info}
        />

        {/* 2. Genesis Identity */}
        <SectionRow
          type="genesis"
          icon="🌟"
          title="Genesis Identity"
          sectionData={data.genesis_identity}
        />

        {/* 3. Relationships */}
        <SectionRow
          type="relationships"
          icon="👥"
          title="Relationships"
          badge={
            <span className="text-xs bg-glass-bg/50 px-1.5 py-0.5 rounded">
              {data.relationships.count}
            </span>
          }
          sectionData={data.relationships}
        />

        {/* 4. Skills */}
        <SectionRow
          type="skills"
          icon="⚡"
          title="Skills"
          badge={
            <span className="text-xs bg-glass-bg/50 px-1.5 py-0.5 rounded">
              {data.skills.totals.total_xp} XP
            </span>
          }
          sectionData={data.skills}
        />

        {/* 5. Wallet */}
        {data.wallet && (
          <SectionRow
            type="wallet"
            icon="💰"
            title="Wallet"
            badge={
              <span className="text-xs text-emerald-400">
                {formatBCH(data.wallet.balance_sats || 0)}
              </span>
            }
            sectionData={data.wallet}
          />
        )}

        {/* Short-Term Memory Section */}
        {shortTermMemory && (
          <>
            {/* 6. Semantic Recalls */}
            <SectionRow
              type="semantic_recalls"
              icon="🔮"
              title="Recalled Memories"
              badge={
                <span className="text-xs bg-purple-500/20 text-purple-400 px-1.5 py-0.5 rounded">
                  {shortTermMemory.semantic_recalls.count}
                </span>
              }
              sectionData={shortTermMemory.semantic_recalls}
            />

            {/* 7. Recent History */}
            <SectionRow
              type="recent_permanent"
              icon="📚"
              title="Recent History"
              badge={
                <span className="text-xs bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded">
                  {shortTermMemory.recent_permanent.count}
                </span>
              }
              sectionData={shortTermMemory.recent_permanent}
            />

            {/* 8. Current Session */}
            <SectionRow
              type="session"
              icon="⚡"
              title="Current Session"
              badge={
                <span className="text-xs bg-accent-warning/20 text-accent-warning px-1.5 py-0.5 rounded">
                  {shortTermMemory.session.count}
                </span>
              }
              sectionData={shortTermMemory.session}
            />
          </>
        )}
      </div>
      )}
    </GlassCard>
  );
};
