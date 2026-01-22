import React, { useState } from 'react';
import { GlassCard } from '../glass';

// ============================================================================
// TYPE DEFINITIONS - Matching chain_state structure
// ============================================================================

interface GenesisIdentity {
  name: string;
  qube_id: string;
  birth_date: string | null;
  genesis_prompt: string;
  favorite_color: string;
  ai_model: string;
  ai_provider: string;
  voice_model: string;
  creator: string;
  nft_category_id: string | null;
  mint_txid: string | null;
  qube_wallet_address: string | null;
  blockchain: string | null;
  available_tools: string[];
}

interface Relationship {
  entity_id: string;
  name: string;
  entity_type: string;
  status: string;
  trust_level: number;
  interaction_count: number;
}

interface SkillInfo {
  skill_id: string;
  name: string;
  xp: number;
  level: number;
  unlocked: boolean;
  tier: string;
  parent_skill?: string;
  tool_unlock?: string;
}

interface SkillCategory {
  category_id: string;
  category_name: string;
  total_xp: number;
  skills: SkillInfo[];
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
  category: string;
}

interface OwnerInfoSummary {
  total_fields: number;
  public_fields: number;
  private_fields: number;
  secret_fields: number;
  categories_populated: number;
  custom_sections: number;
  fields: OwnerInfoField[];
}

interface QubeProfileField {
  key: string;
  value: string;
  sensitivity: 'public' | 'private' | 'secret';
  category: string;
}

interface QubeProfileSummary {
  total_fields: number;
  public_fields: number;
  private_fields: number;
  secret_fields: number;
  categories_populated: number;
  custom_sections: number;
  fields: QubeProfileField[];
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
  last_sync?: number;
}

interface MoodInfo {
  current_mood: string;
  energy_level: number;
  stress_level: number;
  last_update?: number;
}

interface HealthInfo {
  overall_status: string;
  integrity_verified: boolean;
  issues: string[];
  last_check?: number;
}

interface StatsInfo {
  total_tokens: number;
  total_sessions: number;
  total_anchors: number;
  total_cost: number;
  tokens_by_model: Record<string, number>;
  api_calls_by_tool: Record<string, number>;
  first_interaction?: number;
  last_interaction?: number;
  block_counts: Record<string, number>;
}

interface VisualizerSettings {
  enabled: boolean;
  waveform_style: number;
  color_theme: string;
  gradient_style: string;
  sensitivity: number;
  animation_smoothness: string;
  audio_offset_ms: number;
  frequency_range: number;
  output_monitor: number;
}

interface SettingsInfo {
  model_mode?: string;  // "Revolver", "Autonomous", or "Manual" - set by backend handler
  model_locked: boolean;
  model_locked_to?: string;
  revolver_mode_enabled: boolean;
  revolver_mode_pool: string[];
  autonomous_mode_enabled: boolean;
  autonomous_mode_pool: string[];
  // Individual chat auto-anchor settings
  individual_auto_anchor_enabled: boolean;
  individual_auto_anchor_threshold: number;
  // Group chat auto-anchor settings
  group_auto_anchor_enabled: boolean;
  group_auto_anchor_threshold: number;
  // Legacy fields for backwards compatibility
  auto_anchor_enabled?: boolean;
  auto_anchor_threshold?: number;
  tts_enabled: boolean;
  voice_model?: string;
  visualizer?: VisualizerSettings;
}

interface ChainInfo {
  total_blocks: number;
  permanent_blocks: number;
  session_blocks: number;
  last_anchor_block?: number;
  genesis_hash?: string;
  latest_block_hash?: string;
  block_counts: Record<string, number>;
}

interface SessionInfo {
  session_id?: string;
  started_at?: number;
  messages_this_session: number;
}

interface BlockPreview {
  block_number: number;
  block_type: string;
  timestamp?: number;
  preview: string;
  relevance_score?: number;
  is_summary?: boolean;
}

interface MemorySection {
  count: number;
  blocks: BlockPreview[];
}

// Main data structures
interface ActiveContextData {
  genesis_identity: GenesisIdentity;
  relationships: {
    count: number;
    top_relationships: Relationship[];
  };
  skills: {
    totals: SkillsTotals;
    categories: Record<string, SkillCategory>;
  };
  owner_info?: OwnerInfoSummary | null;
  qube_profile?: QubeProfileSummary | null;
  wallet: WalletInfo | null;
  mood?: MoodInfo | null;
  health?: HealthInfo | null;
  stats?: StatsInfo | null;
  settings?: SettingsInfo | null;
  chain?: ChainInfo | null;
  session?: SessionInfo | null;
}

interface ShortTermMemoryData {
  semantic_recalls: MemorySection;
  recent_permanent: MemorySection;
  session: MemorySection;
  estimated_tokens?: number;
  max_context_window?: number;
}

// ============================================================================
// SECTION TYPES FOR SELECTION
// ============================================================================

export type ContextSectionType =
  | 'identity'
  | 'stats'
  | 'session'
  | 'settings'
  | 'relationships'
  | 'skills'
  | 'financial'
  | 'mood'
  | 'health'
  | 'owner_info'
  | 'qube_profile'
  | 'recalled'
  | 'history'
  | 'chain';

export interface ContextSectionData {
  type: ContextSectionType;
  data: any;
  title: string;
  icon: string;
}

// ============================================================================
// COMPONENT PROPS
// ============================================================================

interface ActiveContextPanelProps {
  data: ActiveContextData | null;
  shortTermMemory?: ShortTermMemoryData | null;
  loading?: boolean;
  favoriteColor?: string;
  selectedSection?: ContextSectionType | null;
  onSectionSelect?: (section: ContextSectionData | null) => void;
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

const formatBCH = (sats: number): string => {
  if (!sats) return '0 BCH';
  const bch = sats / 100_000_000;
  if (bch < 0.0001) return `${sats} sats`;
  return `${bch.toFixed(8)} BCH`;
};

const formatTokenCount = (tokens: number): string => {
  if (tokens >= 1000) {
    return `~${(tokens / 1000).toFixed(1)}K`;
  }
  return `~${tokens}`;
};

const getModelModeBadge = (settings?: SettingsInfo | null): string => {
  if (!settings) return 'Manual';
  // Check model_mode string first (set by backend handler, which removes boolean flags)
  if (settings.model_mode) {
    const mode = settings.model_mode.toLowerCase();
    if (mode === 'revolver') return 'Revolver';
    if (mode === 'autonomous') return 'Autonomous';
    if (mode === 'manual') return 'Manual';
  }
  // Fallback to boolean flags (for backwards compatibility)
  if (settings.revolver_mode_enabled) return 'Revolver';
  if (settings.autonomous_mode_enabled) return 'Autonomous';
  if (settings.model_locked) return 'Manual';
  return 'Auto';
};

const getMoodEmoji = (mood?: string): string => {
  const moodEmojis: Record<string, string> = {
    happy: '😊',
    excited: '🤩',
    neutral: '😐',
    curious: '🤔',
    tired: '😴',
    stressed: '😰',
    sad: '😢',
    angry: '😠',
  };
  return moodEmojis[mood || 'neutral'] || '😐';
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export const ActiveContextPanel: React.FC<ActiveContextPanelProps> = ({
  data,
  shortTermMemory,
  loading = false,
  favoriteColor = '#00ff88',
  selectedSection,
  onSectionSelect
}) => {
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

  // Token usage calculations
  const estimatedTokens = shortTermMemory?.estimated_tokens || 0;
  const maxContextWindow = shortTermMemory?.max_context_window || 128000;
  const usagePercent = maxContextWindow > 0 ? (estimatedTokens / maxContextWindow) * 100 : 0;

  const getTokenColor = (): { text: string; bg: string } => {
    if (usagePercent < 25) return { text: 'text-emerald-400', bg: 'bg-emerald-400/20' };
    if (usagePercent < 60) return { text: 'text-yellow-400', bg: 'bg-yellow-400/20' };
    return { text: 'text-red-400', bg: 'bg-red-400/20' };
  };
  const tokenColor = getTokenColor();

  // Handle section click
  const handleSectionClick = (type: ContextSectionType, sectionData: any, title: string, icon: string) => {
    if (onSectionSelect) {
      if (selectedSection === type) {
        onSectionSelect(null);
      } else {
        onSectionSelect({ type, data: sectionData, title, icon });
      }
    }
  };

  // Category row component - minimal, just icon + name + badge
  const CategoryRow: React.FC<{
    type: ContextSectionType;
    icon: string;
    title: string;
    badge?: React.ReactNode;
    sectionData: any;
    disabled?: boolean;
  }> = ({ type, icon, title, badge, sectionData, disabled = false }) => {
    const isSelected = selectedSection === type;
    return (
      <button
        onClick={() => !disabled && handleSectionClick(type, sectionData, title, icon)}
        disabled={disabled}
        className={`w-full flex items-center justify-between py-1.5 px-2 rounded transition-colors ${
          disabled
            ? 'opacity-40 cursor-not-allowed'
            : isSelected
            ? 'bg-accent-primary/20 border border-accent-primary/40'
            : 'hover:bg-glass-bg/30'
        }`}
      >
        <span className="text-sm text-text-secondary flex items-center gap-2">
          <span className="w-5 text-center">{icon}</span>
          <span className={isSelected ? 'text-accent-primary font-medium' : ''}>{title}</span>
        </span>
        <span className="flex items-center gap-2">
          {badge}
          <span className={`text-xs ${isSelected ? 'text-accent-primary' : 'text-text-tertiary'}`}>
            {isSelected ? '◀' : '▶'}
          </span>
        </span>
      </button>
    );
  };

  // Visual separator for memories section
  const MemorySeparator = () => (
    <div className="flex items-center gap-2 py-1.5 px-2">
      <div className="flex-1 h-px bg-gradient-to-r from-transparent via-text-tertiary/30 to-transparent" />
      <span className="text-xs text-text-tertiary uppercase tracking-wider">memories</span>
      <div className="flex-1 h-px bg-gradient-to-r from-transparent via-text-tertiary/30 to-transparent" />
    </div>
  );

  return (
    <GlassCard className="p-3 mb-4 border-l-2" style={{ borderLeftColor: favoriteColor }}>
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between"
      >
        <h3 className="text-lg font-display flex items-center gap-2" style={{ color: favoriteColor }}>
          <span className="text-2xl">🧬</span>
          System State
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
        <div className="space-y-0.5 mt-3">
          {/* Identity (Genesis) */}
          <CategoryRow
            type="identity"
            icon="🌟"
            title="Identity"
            sectionData={data.genesis_identity}
          />

          {/* Stats */}
          <CategoryRow
            type="stats"
            icon="📊"
            title="Stats"
            badge={
              data.stats && (
                <span className="text-xs text-text-tertiary">
                  {data.stats.total_anchors || 0} anchor{(data.stats.total_anchors || 0) !== 1 ? 's' : ''}
                </span>
              )
            }
            sectionData={data.stats}
          />

          {/* Settings */}
          <CategoryRow
            type="settings"
            icon="⚙️"
            title="Settings"
            badge={
              <span className="text-xs text-text-tertiary">
                {getModelModeBadge(data.settings)}
              </span>
            }
            sectionData={data.settings ? { ...data.settings, model_mode: getModelModeBadge(data.settings) } : null}
          />

          {/* Relationships */}
          <CategoryRow
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

          {/* Skills */}
          <CategoryRow
            type="skills"
            icon="🎯"
            title="Skills"
            badge={
              <span className="text-xs text-text-tertiary">
                {data.skills.totals.total_xp} XP
              </span>
            }
            sectionData={data.skills}
          />

          {/* Financial (Wallet) */}
          {data.wallet && (
            <CategoryRow
              type="financial"
              icon="💰"
              title="Financial"
              badge={
                <span className="text-xs text-emerald-400">
                  {formatBCH(data.wallet.balance_sats || 0)}
                </span>
              }
              sectionData={data.wallet}
            />
          )}

          {/* Mood */}
          <CategoryRow
            type="mood"
            icon={getMoodEmoji(data.mood?.current_mood)}
            title="Mood"
            badge={
              data.mood && (
                <span className="text-xs text-text-tertiary capitalize">
                  {data.mood.current_mood}
                </span>
              )
            }
            sectionData={data.mood}
            disabled={!data.mood}
          />

          {/* Health */}
          <CategoryRow
            type="health"
            icon="💚"
            title="Health"
            badge={
              data.health && (
                <span className={`text-xs ${
                  data.health.overall_status === 'healthy' ? 'text-emerald-400' : 'text-yellow-400'
                }`}>
                  {data.health.overall_status}
                </span>
              )
            }
            sectionData={data.health}
            disabled={!data.health}
          />

          {/* Owner Info */}
          <CategoryRow
            type="owner_info"
            icon="👤"
            title="Owner Info"
            badge={
              <span className="text-xs text-text-tertiary">
                {data.owner_info?.total_fields || 0}
              </span>
            }
            sectionData={data.owner_info}
          />

          {/* Qube Profile (Self-identity) */}
          <CategoryRow
            type="qube_profile"
            icon="🪞"
            title={`${data.genesis_identity?.name || 'Qube'}'s Profile`}
            badge={
              <span className="text-xs text-text-tertiary">
                {data.qube_profile?.total_fields || 0}
              </span>
            }
            sectionData={data.qube_profile}
          />

          {/* Memory Separator */}
          <MemorySeparator />

          {/* Session (Current conversation blocks) */}
          <CategoryRow
            type="session"
            icon="⚡"
            title="Session"
            badge={
              shortTermMemory && (
                <span className="text-xs bg-accent-warning/20 text-accent-warning px-1.5 py-0.5 rounded">
                  {shortTermMemory.session.count} {shortTermMemory.session.count === 1 ? 'block' : 'blocks'}
                </span>
              )
            }
            sectionData={{ ...data.session, blocks: shortTermMemory?.session }}
          />

          {/* Recalled Memories (Semantic) */}
          {shortTermMemory && (
            <CategoryRow
              type="recalled"
              icon="🔮"
              title="Recalled"
              badge={
                <span className="text-xs bg-purple-500/20 text-purple-400 px-1.5 py-0.5 rounded">
                  {shortTermMemory.semantic_recalls.count} {shortTermMemory.semantic_recalls.count === 1 ? 'block' : 'blocks'}
                </span>
              }
              sectionData={shortTermMemory.semantic_recalls}
            />
          )}

          {/* History (Recent Permanent) */}
          {shortTermMemory && (
            <CategoryRow
              type="history"
              icon="📚"
              title="History"
              badge={
                <span className="text-xs bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded">
                  {shortTermMemory.recent_permanent.count} {shortTermMemory.recent_permanent.count === 1 ? 'block' : 'blocks'}
                </span>
              }
              sectionData={shortTermMemory.recent_permanent}
            />
          )}

          {/* Chain Info */}
          <CategoryRow
            type="chain"
            icon="🔗"
            title="Chain"
            badge={
              data.chain && (
                <span className="text-xs bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded">
                  {data.chain.total_blocks} {data.chain.total_blocks === 1 ? 'block' : 'blocks'}
                </span>
              )
            }
            sectionData={data.chain}
          />
        </div>
      )}
    </GlassCard>
  );
};
