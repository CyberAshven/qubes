import { calculateTokenCost, formatUSD, formatBCH } from '../../utils/tokenCostCalculator';
import React, { useState, useEffect } from 'react';
import { invoke, convertFileSrc } from '@tauri-apps/api/core';
import { GlassCard, GlassButton } from '../glass';
import { Qube } from '../../types';
import { BlockContentViewer } from '../blocks/BlockContentViewer';
import { SKILL_DEFINITIONS } from '../../data/skillDefinitions';
import { ActiveContextPanel } from '../context';

// Helper to get skill name from ID
const getSkillName = (skillId: string): string => {
  for (const skills of Object.values(SKILL_DEFINITIONS)) {
    const skill = skills.find(s => s.id === skillId);
    if (skill?.name) return skill.name;
  }
  // Fallback: convert ID to title case
  return skillId.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
};

interface Block {
  block_number: number;
  block_hash: string;
  block_type: string;
  timestamp: number;  // Unix timestamp in milliseconds
  creator: string;
  previous_hash: string;
  merkle_root: string;
  signature?: string;
  content: any;
  encrypted: boolean;
  // Token usage tracking (optional fields)
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
  model_used?: string;
  estimated_cost_usd?: number;
  // Relationship delta tracking
  relationship_updates?: Record<string, any>;
  // GAME block multi-signature fields
  participant_signatures?: Array<{
    qube_id: string;
    public_key: string;
    signature: string;
  }>;
  content_hash?: string;
}

interface BlocksTabProps {
  selectedQubes: Qube[];
  userId: string;
  password: string;
  isActive?: boolean;
}

// Unified color scheme for block types and sections
// Block types use these colors consistently across the app
// Active types: GENESIS, MESSAGE, ACTION, SUMMARY, GAME
// Deprecated (removed): THOUGHT, DECISION, OBSERVATION, MEMORY_ANCHOR
const BLOCK_TYPE_COLORS: Record<string, { text: string; bg: string; border: string }> = {
  'GENESIS': { text: 'text-red-500', bg: 'bg-red-500/20', border: 'border-l-red-500' },
  'MESSAGE': { text: 'text-emerald-400', bg: 'bg-emerald-400/20', border: 'border-l-emerald-400' },
  'ACTION': { text: 'text-amber-400', bg: 'bg-amber-400/20', border: 'border-l-amber-400' },
  'SUMMARY': { text: 'text-fuchsia-400', bg: 'bg-fuchsia-400/20', border: 'border-l-fuchsia-400' },
  'GAME': { text: 'text-yellow-400', bg: 'bg-yellow-400/20', border: 'border-l-yellow-400' },
};

// Section colors (where memory came from, not what type it is)
const SECTION_COLORS = {
  recalled: { text: 'text-violet-400', bg: 'bg-violet-400/20', border: 'border-l-violet-400' },  // Semantic recall (AI-driven)
  recent: { text: 'text-slate-400', bg: 'bg-slate-400/20', border: 'border-l-slate-400' },       // Recent history (neutral)
  session: { text: 'text-sky-400', bg: 'bg-sky-400/20', border: 'border-sky-400' },             // Current session (live/active)
};

// Helper function to get color for block type (for badge styling)
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

// Helper function to get ring color for selected block
const getBlockTypeRing = (blockType: string): string => {
  const ringColors: Record<string, string> = {
    'GENESIS': 'ring-red-500',
    'MESSAGE': 'ring-emerald-400',
    'ACTION': 'ring-amber-400',
    'SUMMARY': 'ring-fuchsia-400',
    'GAME': 'ring-yellow-400',
  };
  return ringColors[blockType] || 'ring-text-secondary';
};

// Helper function to get avatar URL for a qube
const getAvatarPath = (qube: Qube, userId: string): string | null => {
  // Priority 1: IPFS URL from backend
  if (qube.avatar_url) return qube.avatar_url;

  // Priority 2: Local file path via Tauri convertFileSrc
  if (qube.avatar_local_path) {
    return convertFileSrc(qube.avatar_local_path);
  }

  // Priority 3: Construct path from qube info (fallback for older qubes)
  if (userId && qube.name && qube.qube_id) {
    const projectRoot = 'C:/Users/bit_f/Projects/Qubes';
    const filePath = `${projectRoot}/data/users/${userId}/qubes/${qube.name}_${qube.qube_id}/chain/${qube.qube_id}_avatar.png`;
    return convertFileSrc(filePath);
  }

  return null;
};

// Selection section types
type SelectionSection = 'recalled' | 'recent' | 'session' | 'permanent';

export const BlocksTab: React.FC<BlocksTabProps> = ({ selectedQubes, userId, password, isActive = false }) => {
  const [sessionBlocks, setSessionBlocks] = useState<Block[]>([]);
  const [permanentBlocks, setPermanentBlocks] = useState<Block[]>([]);

  // Track if initial load has completed for this qube
  // This prevents the tab switch effect from running before initial data is loaded
  const hasInitiallyLoaded = React.useRef(false);

  // Track the qube ID that was loaded - used to detect when we need a fresh load
  const loadedQubeId = React.useRef<string | null>(null);
  const [selectedBlock, setSelectedBlock] = useState<Block | null>(null);
  const [selectedSection, setSelectedSection] = useState<SelectionSection | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [decryptedContent, setDecryptedContent] = useState<any>(null);
  const [showDiscardConfirm, setShowDiscardConfirm] = useState(false);
  const [isAnchoring, setIsAnchoring] = useState(false);
  const [cryptoExpanded, setCryptoExpanded] = useState(false);
  const [contentExpanded, setContentExpanded] = useState(false);
  const [selfEvaluationExpanded, setSelfEvaluationExpanded] = useState(false);
  const [relationshipExpanded, setRelationshipExpanded] = useState(false);
  const [tokenUsageExpanded, setTokenUsageExpanded] = useState(false);
  const [relationshipDeltasExpanded, setRelationshipDeltasExpanded] = useState(false);
  const [skillsExpanded, setSkillsExpanded] = useState(false);

  // Pagination state
  const [sessionBlocksToShow, setSessionBlocksToShow] = useState(10);
  const [permanentBlocksToShow, setPermanentBlocksToShow] = useState(10);

  // Collapsible panel state (collapsed by default)
  const [shortTermExpanded, setShortTermExpanded] = useState(false);
  const [longTermExpanded, setLongTermExpanded] = useState(false);

  // Context preview state
  const [contextPreview, setContextPreview] = useState<any>(null);
  const [contextLoading, setContextLoading] = useState(false);
  const [showContextPanels, setShowContextPanels] = useState(true);

  const selectedQube = selectedQubes.length === 1 ? selectedQubes[0] : null;

  // Reset expanded states when switching blocks
  useEffect(() => {
    setCryptoExpanded(false);
    setContentExpanded(false);
    setTokenUsageExpanded(false);
    setRelationshipDeltasExpanded(false);
    setSkillsExpanded(false);
  }, [selectedBlock?.block_number]);

  // Helper function to truncate hash
  const truncateHash = (hash: string): string => {
    if (!hash || hash === 'N/A') return hash;
    if (hash.length <= 20) return hash;
    return `${hash.slice(0, 8)}...${hash.slice(-8)}`;
  };

  // Helper function to copy hash to clipboard
  const copyToClipboard = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      // You could add a toast notification here if desired
      console.log(`${label} copied to clipboard`);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const loadBlocks = async (): Promise<{ sessionCount: number; permanentCount: number } | null> => {
    console.log('🔍 loadBlocks called, selectedQube:', selectedQube?.qube_id, 'userId:', userId, 'password:', password ? '***' : 'MISSING');
    if (!selectedQube) return null;

    setLoading(true);
    console.log('🚀 About to invoke get_qube_blocks...');
    try {
      const params: any = {
        userId,
        qubeId: selectedQube.qube_id,
      };

      // Only include password if it exists
      if (password) {
        params.password = password;
      }

      const result = await invoke<any>('get_qube_blocks', params);
      console.log('✅ get_qube_blocks returned:', result);

      if (result.success) {
        const sessionCount = result.session_blocks?.length || 0;
        const permanentCount = result.permanent_blocks?.length || 0;
        console.log('Loaded blocks:', { session: sessionCount, permanent: permanentCount });
        setSessionBlocks(result.session_blocks || []);
        setPermanentBlocks(result.permanent_blocks || []);

        // Reset pagination when blocks are loaded
        setSessionBlocksToShow(10);
        setPermanentBlocksToShow(10);
        setLoading(false);

        // Return counts for comparison (don't update lastContextState here -
        // it should only be updated after context is successfully loaded)
        return { sessionCount, permanentCount };
      } else {
        console.error('Failed to load blocks:', result.error);
        alert(`Failed to load blocks: ${result.error}`);
      }
      setLoading(false);
      return null;
    } catch (error) {
      console.error('Failed to load blocks:', error);
      alert(`Failed to load blocks: ${error}`);
      setLoading(false);
      return null;
    }
  };

  // Load context preview (what's actually in the Qube's context window)
  const loadContextPreview = async () => {
    if (!selectedQube || !password) return;

    setContextLoading(true);
    try {
      const result = await invoke<any>('get_context_preview', {
        userId,
        qubeId: selectedQube.qube_id,
        password,
      });

      if (result.success) {
        setContextPreview(result);
        // Note: lastContextState is updated by loadBlocks, not here
        // This ensures we compare apples to apples (both from loadBlocks)
      } else {
        console.warn('Failed to load context preview:', result.error);
        setContextPreview(null);
      }
    } catch (error) {
      console.warn('Failed to load context preview:', error);
      setContextPreview(null);
    } finally {
      setContextLoading(false);
    }
  };

  // Load blocks and context when qube selection changes
  // This is the ONLY place where we do automatic loading
  useEffect(() => {
    const currentQubeId = selectedQube?.qube_id;

    // Check if we already have data for this qube - skip reload if so
    if (currentQubeId && loadedQubeId.current === currentQubeId && hasInitiallyLoaded.current) {
      return;
    }

    // Clear blocks immediately when qube changes to prevent flash of old data
    setSessionBlocks([]);
    setPermanentBlocks([]);
    setSelectedBlock(null);
    setSelectedSection(null);
    setContextPreview(null);
    hasInitiallyLoaded.current = false;
    loadedQubeId.current = null;

    const loadInitial = async () => {
      if (selectedQube) {
        await loadBlocks();
        await loadContextPreview();
        loadedQubeId.current = selectedQube.qube_id;
        hasInitiallyLoaded.current = true;
      }
    };
    loadInitial();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedQube?.qube_id]);

  const handleAnchorSession = async () => {
    if (!selectedQube) return;

    setIsAnchoring(true);
    try {
      await invoke('anchor_session', {
        userId,
        qubeId: selectedQube.qube_id,
        password,
      });
      await loadBlocks();
      // Refresh context preview since blocks changed
      await loadContextPreview();
    } catch (error) {
      console.error('Failed to anchor session:', error);
      alert(`Failed to anchor session: ${error}`);
    } finally {
      setIsAnchoring(false);
    }
  };

  const handleDiscardClick = () => {
    if (!selectedQube || sessionBlocks.length === 0) return;
    setShowDiscardConfirm(true);
  };

  const confirmDiscardAll = async () => {
    if (!selectedQube) return;

    setShowDiscardConfirm(false);

    try {
      console.log('⚡ Proceeding with discard all...');
      const result = await invoke('discard_session', {
        userId,
        qubeId: selectedQube.qube_id,
        password,
      });
      console.log('✅ Discard all completed:', result);
      await loadBlocks();
      // Refresh context preview since blocks changed
      await loadContextPreview();
      setSelectedBlock(null);
      setSelectedSection(null);
    } catch (error) {
      console.error('Failed to discard session:', error);
      alert(`Failed to discard session: ${error}`);
    }
  };

  const confirmDiscardSelected = async () => {
    if (!selectedQube || !selectedBlock || selectedBlock.block_number >= 0) {
      // Only allow discarding session blocks (negative indices)
      alert('Only session blocks can be discarded individually.');
      return;
    }

    setShowDiscardConfirm(false);

    try {
      console.log('⚡ Proceeding with discard selected block:', selectedBlock.block_number);
      const result = await invoke('delete_session_block', {
        userId,
        qubeId: selectedQube.qube_id,
        blockNumber: selectedBlock.block_number,
        password,
      });
      console.log('✅ Discard selected completed:', result);
      await loadBlocks();
      // Refresh context preview since blocks changed
      await loadContextPreview();
      setSelectedBlock(null);
      setSelectedSection(null);
    } catch (error) {
      console.error('Failed to discard block:', error);
      alert(`Failed to discard block: ${error}`);
    }
  };

  const cancelDiscard = () => {
    setShowDiscardConfirm(false);
  };

  const handleBlockClick = (block: Block, section: SelectionSection) => {
    console.log('🔍 Block clicked:', {
      block_number: block.block_number,
      block_type: block.block_type,
      section: section,
      encrypted: block.encrypted,
      content: block.content,
      content_type: typeof block.content,
      content_keys: block.content ? Object.keys(block.content) : 'null'
    });

    try {
      setSelectedBlock(block);
      setSelectedSection(section);
      // All blocks are already decrypted since we prompted for password on load
      setDecryptedContent(block.content);
    } catch (error) {
      console.error('❌ Error setting selected block:', error);
      alert(`Error displaying block: ${error}`);
    }
  };

  const filteredPermanentBlocks = permanentBlocks.filter(block => {
    const matchesSearch = searchQuery === '' ||
      JSON.stringify(block).toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = filterType === 'all' || block.block_type === filterType;
    return matchesSearch && matchesFilter;
  });

  const blockTypes = ['all', 'GENESIS', 'MESSAGE', 'ACTION', 'SUMMARY', 'GAME'];

  if (!selectedQube) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <GlassCard className="p-12 text-center max-w-md">
          <div className="text-6xl mb-4">🧠</div>
          <h2 className="text-2xl font-display text-text-primary mb-2">
            Block Browser
          </h2>
          <p className="text-text-secondary">
            Select a single qube from the roster to view its memory blocks
          </p>
        </GlassCard>
      </div>
    );
  }

  if (selectedQubes.length > 1) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <GlassCard className="p-12 text-center max-w-md">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-display text-text-primary mb-2">
            Multiple Qubes Selected
          </h2>
          <p className="text-text-secondary">
            Please select only one qube to view its blocks
          </p>
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="h-full flex overflow-hidden">
      {/* Left Panel - Block List */}
      <div className="w-2/5 border-r border-glass-border flex flex-col overflow-hidden">
        <div className="p-4 border-b border-glass-border">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-display text-accent-primary">
                Block Browser
              </h1>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowContextPanels(!showContextPanels)}
                className={`p-2 rounded transition-colors ${showContextPanels ? 'bg-accent-primary/20 text-accent-primary' : 'hover:bg-glass-bg/30 text-text-tertiary'}`}
                title={showContextPanels ? "Hide context preview" : "Show context preview"}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </button>
              <button
                onClick={loadBlocks}
                disabled={loading}
                className="p-2 rounded hover:bg-accent-primary/10 text-accent-primary transition-colors disabled:opacity-50"
                title="Refresh blocks"
              >
                <svg
                  className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Context Preview Panels */}
          {showContextPanels && (
            <>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  {/* Qube Avatar */}
                  {selectedQube && getAvatarPath(selectedQube, userId) ? (
                    <img
                      src={getAvatarPath(selectedQube, userId)!}
                      alt={selectedQube.name}
                      className="w-12 h-12 rounded-lg object-cover"
                      style={{
                        borderColor: selectedQube.favorite_color || '#00ff88',
                        borderWidth: '2px',
                        borderStyle: 'solid'
                      }}
                      onError={(e) => {
                        // Fall back to letter avatar if image fails to load
                        const target = e.target as HTMLImageElement;
                        target.style.display = 'none';
                        target.nextElementSibling?.classList.remove('hidden');
                      }}
                    />
                  ) : null}
                  <div
                    className={`w-12 h-12 rounded-lg flex items-center justify-center text-xl font-bold ${selectedQube && getAvatarPath(selectedQube, userId) ? 'hidden' : ''}`}
                    style={{
                      backgroundColor: `${selectedQube?.favorite_color || '#00ff88'}20`,
                      borderColor: selectedQube?.favorite_color || '#00ff88',
                      borderWidth: '2px',
                      borderStyle: 'solid',
                      color: selectedQube?.favorite_color || '#00ff88'
                    }}
                  >
                    {selectedQube?.name?.charAt(0).toUpperCase()}
                  </div>
                  <h2 className="text-2xl font-display font-bold" style={{ color: selectedQube?.favorite_color || '#00ff88' }}>
                    {selectedQube?.name}
                  </h2>
                </div>
                <button
                  onClick={async () => {
                    await loadBlocks();
                    await loadContextPreview();
                  }}
                  disabled={contextLoading || loading}
                  className="text-xs text-accent-primary hover:text-accent-primary/80 transition-colors disabled:opacity-50"
                  title="Refresh blocks and context"
                >
                  {(contextLoading || loading) ? 'Loading...' : 'Refresh'}
                </button>
              </div>
              <ActiveContextPanel
                data={contextPreview?.active_context}
                shortTermMemory={contextPreview?.short_term_memory}
                loading={contextLoading && !contextPreview}
                favoriteColor={selectedQube?.favorite_color}
              />
              <div className="border-b border-glass-border my-4" />
            </>
          )}

          {/* Short-term Memory (All Context Blocks) */}
          <GlassCard className="p-3 mb-4 border-l-2 border-l-amber-400">
            <button
              onClick={() => setShortTermExpanded(!shortTermExpanded)}
              className="w-full flex items-center justify-between"
            >
              <h2 className="text-sm font-display text-amber-400 flex items-center gap-2">
                <span className="text-lg">🧠</span>
                Short-term Memory
                <span className="text-xs bg-amber-400/20 text-amber-400 px-1.5 py-0.5 rounded">
                  {(() => {
                    const count = sessionBlocks.length + (contextPreview?.short_term_memory?.recent_permanent?.count || 0) + (contextPreview?.short_term_memory?.semantic_recalls?.count || 0);
                    return `${count} ${count === 1 ? 'block' : 'blocks'}`;
                  })()}
                </span>
              </h2>
              <div className="flex items-center gap-2">
                {shortTermExpanded && sessionBlocks.length > 10 && (
                  <span
                    onClick={(e) => { e.stopPropagation(); setSessionBlocksToShow(sessionBlocks.length); }}
                    className="text-xs text-text-secondary hover:text-text-primary transition-colors"
                  >
                    Show All
                  </span>
                )}
                {shortTermExpanded && sessionBlocksToShow > 10 && (
                  <span
                    onClick={(e) => { e.stopPropagation(); setSessionBlocksToShow(10); }}
                    className="text-xs text-text-secondary hover:text-text-primary transition-colors"
                  >
                    Minimize
                  </span>
                )}
                <span className="text-text-tertiary">{shortTermExpanded ? '▼' : '▶'}</span>
              </div>
            </button>

            {shortTermExpanded && (
              <>
            {/* Recalled Memories from Context */}
            {contextPreview?.short_term_memory?.semantic_recalls?.blocks?.length > 0 && (
              <div className="mb-3">
                <div className={`text-xs ${SECTION_COLORS.recalled.text} mb-2 flex items-center gap-2`}>
                  <span>🔮</span> Recalled Memories
                  <span className={`${SECTION_COLORS.recalled.bg} ${SECTION_COLORS.recalled.text} px-1.5 py-0.5 rounded`}>
                    {contextPreview.short_term_memory.semantic_recalls.count}
                  </span>
                </div>
                <div className="space-y-2">
                  {contextPreview.short_term_memory.semantic_recalls.blocks.map((block: any, idx: number) => (
                    <GlassCard
                      key={`recalled-${idx}`}
                      variant="interactive"
                      className={`p-3 cursor-pointer border-l-2 ${getBlockTypeBorder(block.block_type)} ${
                        selectedBlock?.block_number === block.block_number && selectedSection === 'recalled'
                          ? `ring-2 ${getBlockTypeRing(block.block_type)}`
                          : ''
                      }`}
                      onClick={() => {
                        // Find the full block from permanentBlocks if available
                        const fullBlock = permanentBlocks.find(b => b.block_number === block.block_number);
                        if (fullBlock) handleBlockClick(fullBlock, 'recalled');
                      }}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-mono text-text-primary">
                          Block #{block.block_number}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className={`text-xs ${SECTION_COLORS.recalled.text}`}>
                            {Math.round((block.relevance_score || 0) * 100)}%
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded ${getBlockTypeColor(block.block_type)}`}>
                            {block.block_type}
                          </span>
                        </div>
                      </div>
                      <div className="text-xs text-text-tertiary">
                        {block.timestamp && new Date(block.timestamp > 1e12 ? block.timestamp : block.timestamp * 1000).toLocaleString()}
                      </div>
                    </GlassCard>
                  ))}
                </div>
              </div>
            )}

            {/* Recent History from Context */}
            {contextPreview?.short_term_memory?.recent_permanent?.blocks?.length > 0 && (
              <div className="mb-3">
                <div className={`text-xs ${SECTION_COLORS.recent.text} mb-2 flex items-center gap-2`}>
                  <span>📚</span> Recent History
                  <span className={`${SECTION_COLORS.recent.bg} ${SECTION_COLORS.recent.text} px-1.5 py-0.5 rounded`}>
                    {contextPreview.short_term_memory.recent_permanent.count}
                  </span>
                </div>
                <div className="space-y-2">
                  {contextPreview.short_term_memory.recent_permanent.blocks.map((block: any, idx: number) => (
                    <GlassCard
                      key={`recent-${idx}`}
                      variant="interactive"
                      className={`p-3 cursor-pointer border-l-2 ${getBlockTypeBorder(block.block_type)} ${
                        selectedBlock?.block_number === block.block_number && selectedSection === 'recent'
                          ? `ring-2 ${getBlockTypeRing(block.block_type)}`
                          : ''
                      }`}
                      onClick={() => {
                        const fullBlock = permanentBlocks.find(b => b.block_number === block.block_number);
                        if (fullBlock) handleBlockClick(fullBlock, 'recent');
                      }}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-mono text-text-primary">
                          Block #{block.block_number}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded ${getBlockTypeColor(block.block_type)}`}>
                          {block.block_type}
                        </span>
                      </div>
                      <div className="text-xs text-text-tertiary">
                        {block.timestamp && new Date(block.timestamp > 1e12 ? block.timestamp : block.timestamp * 1000).toLocaleString()}
                      </div>
                    </GlassCard>
                  ))}
                </div>
              </div>
            )}

            {/* Session Blocks */}
            {sessionBlocks.length > 0 ? (
              <>
                <div className={`text-xs ${SECTION_COLORS.session.text} mb-2 flex items-center gap-2`}>
                  <span>⚡</span> Current Session
                  <span className={`${SECTION_COLORS.session.bg} ${SECTION_COLORS.session.text} px-1.5 py-0.5 rounded`}>
                    {sessionBlocks.length}
                  </span>
                </div>
                <div className="flex gap-2 mb-3">
                  <GlassButton
                    variant="primary"
                    onClick={handleAnchorSession}
                    className="flex-1 text-sm"
                  >
                    ⚓ Anchor Session
                  </GlassButton>
                  <GlassButton
                    variant="danger"
                    onClick={handleDiscardClick}
                    className="flex-1 text-sm"
                  >
                    🗑️ Discard
                  </GlassButton>
                </div>

                <div className="space-y-2">
                  {sessionBlocks.slice(0, sessionBlocksToShow).map((block) => (
                    <GlassCard
                      key={block.block_number}
                      variant="interactive"
                      className={`p-3 cursor-pointer border-l-2 ${getBlockTypeBorder(block.block_type)} border border-dashed ${SECTION_COLORS.session.border}/30 bg-sky-400/5 ${
                        selectedBlock?.block_number === block.block_number && selectedSection === 'session'
                          ? `ring-2 ${getBlockTypeRing(block.block_type)}`
                          : ''
                      }`}
                      onClick={() => handleBlockClick(block, 'session')}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className={`text-sm font-mono ${SECTION_COLORS.session.text}`}>
                          Block #{block.block_number}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded ${getBlockTypeColor(block.block_type)}`}>
                          {block.block_type}
                        </span>
                      </div>
                      <div className="text-xs text-text-tertiary">
                        {new Date(block.timestamp).toLocaleString()}
                      </div>
                    </GlassCard>
                  ))}
                </div>

                {sessionBlocks.length > sessionBlocksToShow && (
                  <div className="mt-3 text-center">
                    <button
                      onClick={() => setSessionBlocksToShow(prev => Math.min(prev + 10, sessionBlocks.length))}
                      className="text-sm text-text-secondary hover:text-text-primary transition-colors px-4 py-2 rounded bg-glass-bg/30 hover:bg-glass-bg/50"
                    >
                      Show More ({sessionBlocks.length - sessionBlocksToShow} remaining)
                    </button>
                  </div>
                )}
              </>
            ) : (
              <div className={`text-center py-8 text-text-tertiary text-sm border-2 border-dashed ${SECTION_COLORS.session.border}/20 rounded-lg`}>
                No session blocks - start a conversation to create short-term memories
              </div>
            )}
              </>
            )}
          </GlassCard>

          {/* Long-term Memory (Permanent Blocks) */}
          <GlassCard className="p-3 mb-4 border-l-2 border-l-cyan-400">
            <button
              onClick={() => setLongTermExpanded(!longTermExpanded)}
              className="w-full flex items-center justify-between"
            >
              <h2 className="text-sm font-display text-cyan-400 flex items-center gap-2">
                <span className="text-lg">💾</span>
                Long-term Memory
                <span className="text-xs bg-cyan-400/20 text-cyan-400 px-1.5 py-0.5 rounded">
                  {permanentBlocks.length} {permanentBlocks.length === 1 ? 'block' : 'blocks'}
                </span>
              </h2>
              <div className="flex items-center gap-2">
                {longTermExpanded && filteredPermanentBlocks.length > 10 && (
                  <span
                    onClick={(e) => { e.stopPropagation(); setPermanentBlocksToShow(filteredPermanentBlocks.length); }}
                    className="text-xs text-text-secondary hover:text-text-primary transition-colors"
                  >
                    Show All
                  </span>
                )}
                {longTermExpanded && permanentBlocksToShow > 10 && (
                  <span
                    onClick={(e) => { e.stopPropagation(); setPermanentBlocksToShow(10); }}
                    className="text-xs text-text-secondary hover:text-text-primary transition-colors"
                  >
                    Minimize
                  </span>
                )}
                <span className="text-text-tertiary">{longTermExpanded ? '▼' : '▶'}</span>
              </div>
            </button>

            {longTermExpanded && (
              <>
            {/* Search and Filter */}
            <div className="space-y-2 mb-3">
              <input
                type="text"
                placeholder="Search blocks..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-3 py-2 bg-glass-bg backdrop-blur-glass border border-glass-border rounded-lg text-text-primary text-sm placeholder-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
              />
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="w-full px-3 py-2 bg-glass-bg backdrop-blur-glass border border-glass-border rounded-lg text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
              >
                {blockTypes.map((type) => (
                  <option key={type} value={type}>
                    {type === 'all' ? 'All Types' : type}
                  </option>
                ))}
              </select>
            </div>

            {/* Block List */}
            <div className="space-y-2">
              {filteredPermanentBlocks.length === 0 ? (
                <div className="text-center py-8 text-text-tertiary text-sm">
                  {permanentBlocks.length === 0
                    ? 'No permanent blocks yet'
                    : 'No blocks match your search'}
                </div>
              ) : (
                <>
                  {filteredPermanentBlocks.slice(0, permanentBlocksToShow).map((block) => (
                    <GlassCard
                      key={block.block_number}
                      variant="interactive"
                      className={`p-3 cursor-pointer border-l-2 ${getBlockTypeBorder(block.block_type)} ${
                        selectedBlock?.block_number === block.block_number && selectedSection === 'permanent'
                          ? `ring-2 ${getBlockTypeRing(block.block_type)}`
                          : ''
                      }`}
                      onClick={() => handleBlockClick(block, 'permanent')}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-mono text-text-primary">
                          Block #{block.block_number}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded ${getBlockTypeColor(block.block_type)}`}>
                          {block.block_type}
                        </span>
                      </div>
                      <div className="text-xs text-text-tertiary">
                        {new Date(block.timestamp).toLocaleString()}
                      </div>
                    </GlassCard>
                  ))}

                  {filteredPermanentBlocks.length > permanentBlocksToShow && (
                    <div className="mt-3 text-center">
                      <button
                        onClick={() => setPermanentBlocksToShow(prev => Math.min(prev + 10, filteredPermanentBlocks.length))}
                        className="text-sm text-text-secondary hover:text-text-primary transition-colors px-4 py-2 rounded bg-glass-bg/30 hover:bg-glass-bg/50"
                      >
                        Show More ({filteredPermanentBlocks.length - permanentBlocksToShow} remaining)
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
              </>
            )}
          </GlassCard>
        </div>
      </div>

      {/* Right Panel - Block Detail Viewer */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-6">
        {!selectedBlock ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="text-6xl mb-4">📄</div>
              <h2 className="text-xl font-display text-text-primary mb-2">
                No Block Selected
              </h2>
              <p className="text-text-secondary">
                Click on a block to view its details
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-4 max-w-4xl">
            {/* Metadata Card */}
            <GlassCard className="p-6">
              <h2 className="text-xl font-display text-accent-primary mb-4 flex items-center gap-2">
                Block #{selectedBlock.block_number}
                <span className={`text-sm px-3 py-1 rounded ${getBlockTypeColor(selectedBlock.block_type)}`}>
                  {selectedBlock.block_type}
                </span>
              </h2>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-text-tertiary">Timestamp:</span>
                  <div className="text-text-primary mt-1">
                    {new Date(selectedBlock.timestamp).toLocaleString()}
                  </div>
                </div>
                <div>
                  <span className="text-text-tertiary">Creator:</span>
                  <div className="text-text-primary mt-1">
                    {selectedBlock.creator}
                  </div>
                </div>
                <div>
                  <span className="text-text-tertiary">Encrypted:</span>
                  <div className="text-text-primary mt-1">
                    {selectedBlock.encrypted ? '🔒 Yes' : '🔓 No'}
                  </div>
                </div>
              </div>
            </GlassCard>

            {/* Cryptographic Data Card */}
            <GlassCard className="p-6">
              <button
                onClick={() => setCryptoExpanded(!cryptoExpanded)}
                className="w-full flex items-center justify-between text-lg font-display text-accent-primary hover:text-accent-primary/80 transition-colors"
              >
                <span>Cryptographic Data</span>
                <span className="text-2xl">{cryptoExpanded ? '▼' : '▶'}</span>
              </button>

              {cryptoExpanded && (
                <div className="space-y-3 text-sm mt-4">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-text-tertiary">Block Hash:</span>
                      <button
                        onClick={() => copyToClipboard(selectedBlock.block_hash, 'Block Hash')}
                        className="text-xs px-2 py-1 rounded bg-accent-primary/20 hover:bg-accent-primary/30 text-accent-primary transition-colors"
                      >
                        Copy
                      </button>
                    </div>
                    <div className="font-mono text-xs text-text-primary break-all bg-bg-tertiary p-2 rounded">
                      {selectedBlock.block_hash}
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-text-tertiary">Previous Hash:</span>
                      <button
                        onClick={() => copyToClipboard(selectedBlock.previous_hash, 'Previous Hash')}
                        className="text-xs px-2 py-1 rounded bg-accent-primary/20 hover:bg-accent-primary/30 text-accent-primary transition-colors"
                      >
                        Copy
                      </button>
                    </div>
                    <div className="font-mono text-xs text-text-primary break-all bg-bg-tertiary p-2 rounded">
                      {selectedBlock.previous_hash}
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-text-tertiary">Signature:</span>
                      {selectedBlock.signature && selectedBlock.signature !== 'N/A' && (
                        <button
                          onClick={() => copyToClipboard(selectedBlock.signature!, 'Signature')}
                          className="text-xs px-2 py-1 rounded bg-accent-primary/20 hover:bg-accent-primary/30 text-accent-primary transition-colors"
                        >
                          Copy
                        </button>
                      )}
                    </div>
                    <div className="font-mono text-xs text-text-primary break-all bg-bg-tertiary p-2 rounded">
                      {selectedBlock.signature || 'N/A'}
                    </div>
                  </div>
                  {selectedBlock.merkle_root && selectedBlock.merkle_root !== 'N/A' && (
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-text-tertiary">Merkle Root:</span>
                        <button
                          onClick={() => copyToClipboard(selectedBlock.merkle_root!, 'Merkle Root')}
                          className="text-xs px-2 py-1 rounded bg-accent-primary/20 hover:bg-accent-primary/30 text-accent-primary transition-colors"
                        >
                          Copy
                        </button>
                      </div>
                      <div className="font-mono text-xs text-text-primary break-all bg-bg-tertiary p-2 rounded">
                        {selectedBlock.merkle_root}
                      </div>
                    </div>
                  )}

                  {/* Multi-Signature Display (for GAME blocks) */}
                  {selectedBlock.participant_signatures && selectedBlock.participant_signatures.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-amber-400/20">
                      <div className="text-amber-400 mb-2 font-semibold flex items-center gap-2">
                        <span>🎮</span>
                        <span>Participant Signatures ({selectedBlock.participant_signatures.length}):</span>
                      </div>
                      {selectedBlock.content_hash && (
                        <div className="mb-3">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-text-tertiary text-xs">Content Hash (signed by all):</span>
                            <button
                              onClick={() => copyToClipboard(selectedBlock.content_hash!, 'Content Hash')}
                              className="text-xs px-2 py-0.5 rounded bg-amber-400/20 hover:bg-amber-400/30 text-amber-400 transition-colors"
                            >
                              Copy
                            </button>
                          </div>
                          <div className="font-mono text-xs text-text-primary break-all bg-bg-tertiary p-2 rounded">
                            {selectedBlock.content_hash}
                          </div>
                        </div>
                      )}
                      <div className="space-y-2 max-h-64 overflow-y-auto">
                        {selectedBlock.participant_signatures.map((sig) => (
                          <div key={sig.qube_id} className="bg-bg-tertiary/50 p-3 rounded border border-amber-400/20">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-sm text-amber-400 font-semibold">Qube: {sig.qube_id}</span>
                              <span className="text-xs text-green-400">✓ Verified</span>
                            </div>
                            <div className="mb-2">
                              <div className="text-xs text-text-tertiary mb-1">Public Key:</div>
                              <div className="font-mono text-xs text-text-primary break-all bg-bg-tertiary p-1 rounded">
                                {sig.public_key.slice(0, 40)}...
                              </div>
                            </div>
                            <div>
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-xs text-text-tertiary">Signature:</span>
                                <button
                                  onClick={() => copyToClipboard(sig.signature, `Signature for ${sig.qube_id}`)}
                                  className="text-xs px-2 py-0.5 rounded bg-amber-400/20 hover:bg-amber-400/30 text-amber-400 transition-colors"
                                >
                                  Copy
                                </button>
                              </div>
                              <div className="font-mono text-xs text-text-primary break-all bg-bg-tertiary p-1 rounded">
                                {sig.signature.slice(0, 60)}...
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Multi-Signature Display (for group conversation blocks - legacy format) */}
                  {selectedBlock.content?.participant_signatures && Object.keys(selectedBlock.content.participant_signatures).length > 0 && (
                    <div className="mt-4 pt-4 border-t border-accent-primary/20">
                      <div className="text-text-secondary mb-2 font-semibold">
                        Participant Signatures ({Object.keys(selectedBlock.content.participant_signatures).length}):
                      </div>
                      <div className="space-y-2 max-h-64 overflow-y-auto">
                        {Object.entries(selectedBlock.content.participant_signatures).map(([qubeId, signature]: [string, any]) => (
                          <div key={qubeId} className="bg-bg-tertiary/50 p-2 rounded">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs text-accent-primary font-mono">{qubeId.slice(0, 12)}...</span>
                              <button
                                onClick={() => copyToClipboard(signature as string, `Signature for ${qubeId}`)}
                                className="text-xs px-2 py-0.5 rounded bg-accent-primary/20 hover:bg-accent-primary/30 text-accent-primary transition-colors"
                              >
                                Copy
                              </button>
                            </div>
                            <div className="font-mono text-xs text-text-primary break-all">
                              {(signature as string).slice(0, 60)}...
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </GlassCard>

            {/* Token Usage & Cost Card */}
            {(selectedBlock.input_tokens || selectedBlock.output_tokens || selectedBlock.total_tokens) && (
              <GlassCard className="p-6">
                <button
                  onClick={() => setTokenUsageExpanded(!tokenUsageExpanded)}
                  className="w-full flex items-center justify-between text-lg font-display text-accent-primary hover:text-accent-primary/80 transition-colors"
                >
                  <span>Token Usage & Cost</span>
                  <span className="text-2xl">{tokenUsageExpanded ? '▼' : '▶'}</span>
                </button>

                {tokenUsageExpanded && (() => {
                  const cost = selectedBlock.model_used && selectedBlock.input_tokens != null && selectedBlock.output_tokens != null
                    ? calculateTokenCost(selectedBlock.model_used, selectedBlock.input_tokens, selectedBlock.output_tokens)
                    : null;

                  return (
                    <div className="space-y-3 text-sm mt-4">
                      {selectedBlock.model_used && (
                        <div className="flex justify-between py-2 border-b border-accent-primary/20">
                          <span className="text-text-secondary">Model Used:</span>
                          <span className="font-mono text-accent-primary">{selectedBlock.model_used}</span>
                        </div>
                      )}

                      {selectedBlock.input_tokens != null && (
                        <div className="flex justify-between py-2 border-b border-accent-primary/20">
                          <span className="text-text-secondary">Input Tokens:</span>
                          <span className="font-mono text-text-primary">{selectedBlock.input_tokens.toLocaleString()}</span>
                        </div>
                      )}

                      {selectedBlock.output_tokens != null && (
                        <div className="flex justify-between py-2 border-b border-accent-primary/20">
                          <span className="text-text-secondary">Output Tokens:</span>
                          <span className="font-mono text-text-primary">{selectedBlock.output_tokens.toLocaleString()}</span>
                        </div>
                      )}

                      {selectedBlock.total_tokens != null && (
                        <div className="flex justify-between py-2 border-b border-accent-primary/20">
                          <span className="text-text-secondary">Total Tokens:</span>
                          <span className="font-mono text-accent-secondary">{selectedBlock.total_tokens.toLocaleString()}</span>
                        </div>
                      )}

                      {cost && (
                        <>
                          <div className="flex justify-between py-2 border-b border-accent-success/20">
                            <span className="text-text-secondary">Estimated Cost (USD):</span>
                            <span className="font-mono text-accent-success">${formatUSD(cost.usd)}</span>
                          </div>
                          <div className="flex justify-between py-2">
                            <span className="text-text-secondary">Estimated Cost (BCH):</span>
                            <span className="font-mono text-accent-success">{formatBCH(cost.bch)} BCH</span>
                          </div>
                        </>
                      )}
                    </div>
                  );
                })()}
              </GlassCard>
            )}

            {/* Relationship Deltas Card */}
            {selectedBlock.relationship_updates && Object.keys(selectedBlock.relationship_updates).length > 0 && (
              <GlassCard className="p-6">
                <button
                  onClick={() => setRelationshipDeltasExpanded(!relationshipDeltasExpanded)}
                  className="w-full flex items-center justify-between text-lg font-display text-accent-primary hover:text-accent-primary/80 transition-colors"
                >
                  <span className="flex items-center gap-2">
                    <span>Relationship Progression</span>
                    <span className="text-xs bg-accent-primary/20 text-accent-primary px-2 py-0.5 rounded-full">
                      {Object.keys(selectedBlock.relationship_updates).length}
                    </span>
                  </span>
                  <span className="text-2xl">{relationshipDeltasExpanded ? '▼' : '▶'}</span>
                </button>

                {relationshipDeltasExpanded && (
                  <div className="space-y-4 mt-4">
                    {Object.entries(selectedBlock.relationship_updates).map(([entityId, deltas]: [string, any]) => {
                      // Try to find entity name from selectedQubes
                      const entityName = selectedQubes.find(q => q.qube_id === entityId)?.name || entityId;

                      return (
                        <div key={entityId} className="border border-accent-primary/20 rounded-lg p-4 bg-bg-tertiary/30">
                          {/* Entity Header */}
                          <div className="flex items-center gap-2 mb-3 pb-2 border-b border-accent-primary/10">
                            <span className="text-accent-primary font-semibold">👤</span>
                            <span className="text-text-primary font-medium">{entityName}</span>
                            {entityId !== entityName && (
                              <span className="text-xs text-text-tertiary font-mono">({entityId.slice(0, 8)}...)</span>
                            )}
                          </div>

                          <div className="space-y-2 text-sm">
                            {/* Message Counters */}
                            {(deltas.messages_sent_delta !== undefined || deltas.messages_received_delta !== undefined) && (
                              <div className="grid grid-cols-2 gap-2">
                                {deltas.messages_sent_delta !== undefined && deltas.messages_sent_delta !== 0 && (
                                  <div className="flex justify-between">
                                    <span className="text-text-tertiary">Messages Sent:</span>
                                    <span className={`font-mono ${deltas.messages_sent_delta > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                      {deltas.messages_sent_delta > 0 ? '+' : ''}{deltas.messages_sent_delta}
                                    </span>
                                  </div>
                                )}
                                {deltas.messages_received_delta !== undefined && deltas.messages_received_delta !== 0 && (
                                  <div className="flex justify-between">
                                    <span className="text-text-tertiary">Messages Received:</span>
                                    <span className={`font-mono ${deltas.messages_received_delta > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                      {deltas.messages_received_delta > 0 ? '+' : ''}{deltas.messages_received_delta}
                                    </span>
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Collaboration Counters */}
                            {(deltas.collaborations_delta !== undefined || deltas.successful_collaborations_delta !== undefined || deltas.failed_collaborations_delta !== undefined) && (
                              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-accent-primary/10">
                                {deltas.collaborations_delta !== undefined && deltas.collaborations_delta !== 0 && (
                                  <div className="flex justify-between">
                                    <span className="text-text-tertiary">Collaborations:</span>
                                    <span className={`font-mono ${deltas.collaborations_delta > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                      {deltas.collaborations_delta > 0 ? '+' : ''}{deltas.collaborations_delta}
                                    </span>
                                  </div>
                                )}
                                {deltas.successful_collaborations_delta !== undefined && deltas.successful_collaborations_delta !== 0 && (
                                  <div className="flex justify-between">
                                    <span className="text-text-tertiary">✓ Successful:</span>
                                    <span className="font-mono text-green-400">
                                      +{deltas.successful_collaborations_delta}
                                    </span>
                                  </div>
                                )}
                                {deltas.failed_collaborations_delta !== undefined && deltas.failed_collaborations_delta !== 0 && (
                                  <div className="flex justify-between">
                                    <span className="text-text-tertiary">✗ Failed:</span>
                                    <span className="font-mono text-red-400">
                                      +{deltas.failed_collaborations_delta}
                                    </span>
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Trust Updates */}
                            {deltas.trust_updates && Object.keys(deltas.trust_updates).length > 0 && (
                              <div className="pt-2 border-t border-accent-primary/10">
                                <div className="text-text-secondary font-semibold mb-1.5">Trust Changes:</div>
                                <div className="grid grid-cols-2 gap-2">
                                  {Object.entries(deltas.trust_updates).map(([component, delta]: [string, any]) => (
                                    <div key={component} className="flex justify-between">
                                      <span className="text-text-tertiary capitalize">{component}:</span>
                                      <span className={`font-mono ${delta > 0 ? 'text-green-400' : delta < 0 ? 'text-red-400' : 'text-text-tertiary'}`}>
                                        {delta > 0 ? '+' : ''}{typeof delta === 'number' ? delta.toFixed(1) : delta}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Shared Experience */}
                            {deltas.shared_experience && (
                              <div className="pt-2 border-t border-accent-primary/10">
                                <div className="text-text-secondary font-semibold mb-1">Shared Experience:</div>
                                <div className="bg-bg-tertiary/50 p-2 rounded text-xs">
                                  <div className="flex items-start gap-2">
                                    <span className="text-lg">
                                      {deltas.shared_experience.sentiment === 'positive' ? '😊' :
                                       deltas.shared_experience.sentiment === 'negative' ? '😞' :
                                       deltas.shared_experience.sentiment === 'significant' ? '⭐' : '📝'}
                                    </span>
                                    <div className="flex-1">
                                      <div className="text-text-primary font-medium mb-0.5">
                                        {deltas.shared_experience.event}
                                      </div>
                                      {deltas.shared_experience.details && (
                                        <div className="text-text-tertiary mt-1">
                                          {JSON.stringify(deltas.shared_experience.details, null, 2)}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            )}

                            {/* Interaction Timestamp */}
                            {deltas.interaction_timestamp && (
                              <div className="pt-2 border-t border-accent-primary/10 flex justify-between">
                                <span className="text-text-tertiary">Last Interaction:</span>
                                <span className="text-text-primary text-xs">
                                  {new Date(deltas.interaction_timestamp * 1000).toLocaleString()}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </GlassCard>
            )}

            {/* Self Evaluation Card - Only for SUMMARY blocks */}
            {selectedBlock.block_type === 'SUMMARY' && decryptedContent?.self_evaluation && (
              <GlassCard className="p-6 mb-4">
                <button
                  onClick={() => setSelfEvaluationExpanded(!selfEvaluationExpanded)}
                  className="w-full flex items-center justify-between text-lg font-display text-accent-primary hover:text-accent-primary/80 transition-colors mb-4"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">🪞</span>
                    <span>Self Evaluation</span>
                  </div>
                  <span className="text-2xl">{selfEvaluationExpanded ? '▼' : '▶'}</span>
                </button>

                {selfEvaluationExpanded && (
                  <div className="space-y-4">
                    {/* Evaluation Summary */}
                    {decryptedContent.self_evaluation.evaluation_summary && (
                      <div className="border border-glass-border/50 rounded-lg p-4 bg-glass-light/30">
                        <div className="text-xs text-accent-secondary mb-2 font-semibold">Summary</div>
                        <p className="text-sm text-text-secondary italic">
                          "{decryptedContent.self_evaluation.evaluation_summary}"
                        </p>
                      </div>
                    )}

                    {/* Overall Score */}
                    {decryptedContent.self_evaluation.metrics && Object.keys(decryptedContent.self_evaluation.metrics).length > 0 && (
                      <div className="border border-glass-border/50 rounded-lg p-4 bg-glass-light/30">
                        <div className="text-xs text-accent-secondary mb-3 font-semibold">Overall Score</div>
                        <div className="flex items-center gap-3">
                          <div className="flex-1">
                            <div className="h-2 bg-bg-tertiary rounded-full overflow-hidden">
                              <div
                                className="h-full bg-gradient-to-r from-accent-primary to-accent-secondary transition-all duration-300"
                                style={{
                                  width: `${(Object.values(decryptedContent.self_evaluation.metrics).reduce((a: number, b: any) => a + (typeof b === 'number' ? b : 0), 0) / Object.keys(decryptedContent.self_evaluation.metrics).length)}%`
                                }}
                              />
                            </div>
                          </div>
                          <span className="text-2xl font-bold text-accent-primary">
                            {(Object.values(decryptedContent.self_evaluation.metrics).reduce((a: number, b: any) => a + (typeof b === 'number' ? b : 0), 0) / Object.keys(decryptedContent.self_evaluation.metrics).length).toFixed(1)}
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Metrics Grid */}
                    {decryptedContent.self_evaluation.metrics && Object.keys(decryptedContent.self_evaluation.metrics).length > 0 && (
                      <div className="border border-glass-border/50 rounded-lg p-4 bg-glass-light/30">
                        <div className="text-xs text-accent-secondary mb-3 font-semibold">Performance Metrics</div>
                        <div className="grid grid-cols-2 gap-3">
                          {Object.entries(decryptedContent.self_evaluation.metrics).map(([metric, value]: [string, any]) => {
                            const score = typeof value === 'number' ? value : 0;
                            const colorClass = score >= 80 ? 'text-green-400' : score >= 60 ? 'text-yellow-400' : 'text-orange-400';

                            return (
                              <div key={metric} className="flex flex-col gap-1">
                                <div className="flex items-center justify-between text-xs">
                                  <span className="text-text-tertiary capitalize">{metric.replace(/_/g, ' ')}</span>
                                  <span className={`font-bold ${colorClass}`}>{score.toFixed(0)}</span>
                                </div>
                                <div className="h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
                                  <div
                                    className={`h-full transition-all duration-300 ${
                                      score >= 80 ? 'bg-green-400' : score >= 60 ? 'bg-yellow-400' : 'bg-orange-400'
                                    }`}
                                    style={{ width: `${score}%` }}
                                  />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Strengths */}
                    {decryptedContent.self_evaluation.strengths && decryptedContent.self_evaluation.strengths.length > 0 && (
                      <div className="border border-glass-border/50 rounded-lg p-4 bg-glass-light/30">
                        <div className="text-xs text-accent-secondary mb-3 font-semibold flex items-center gap-2">
                          <span>💪</span>
                          <span>Strengths</span>
                        </div>
                        <ul className="space-y-2">
                          {decryptedContent.self_evaluation.strengths.map((strength: string, idx: number) => (
                            <li key={idx} className="flex items-start gap-2 text-sm text-text-secondary">
                              <span className="text-green-400 mt-0.5">✓</span>
                              <span>{strength}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Areas for Improvement */}
                    {decryptedContent.self_evaluation.areas_for_improvement && decryptedContent.self_evaluation.areas_for_improvement.length > 0 && (
                      <div className="border border-glass-border/50 rounded-lg p-4 bg-glass-light/30">
                        <div className="text-xs text-accent-secondary mb-3 font-semibold flex items-center gap-2">
                          <span>📈</span>
                          <span>Areas for Improvement</span>
                        </div>
                        <ul className="space-y-2">
                          {decryptedContent.self_evaluation.areas_for_improvement.map((area: string, idx: number) => (
                            <li key={idx} className="flex items-start gap-2 text-sm text-text-secondary">
                              <span className="text-accent-warning mt-0.5">→</span>
                              <span>{area}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Reasoning */}
                    {decryptedContent.self_evaluation.reasoning && (
                      <div className="border border-glass-border/50 rounded-lg p-4 bg-glass-light/30">
                        <div className="text-xs text-accent-secondary mb-2 font-semibold">Reasoning</div>
                        <p className="text-sm text-text-tertiary leading-relaxed">
                          {decryptedContent.self_evaluation.reasoning}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </GlassCard>
            )}

            {/* Skills Progression Card - Only for SUMMARY blocks */}
            {selectedBlock.block_type === 'SUMMARY' && decryptedContent?.skill_detections && decryptedContent.skill_detections.length > 0 && (
              <GlassCard className="p-6 mb-4">
                <button
                  onClick={() => setSkillsExpanded(!skillsExpanded)}
                  className="w-full flex items-center justify-between text-lg font-display text-accent-primary hover:text-accent-primary/80 transition-colors mb-4"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">⭐</span>
                    <span>Skills Progression</span>
                    <span className="text-sm text-text-tertiary">
                      (+{decryptedContent.skill_detections.reduce((sum: number, d: any) => sum + (d.xp_amount || 0), 0)} XP)
                    </span>
                  </div>
                  <span className="text-2xl">{skillsExpanded ? '▼' : '▶'}</span>
                </button>

                {skillsExpanded && (() => {
                  // Group skill detections by skill_id
                  const groupedSkills: Record<string, { total_xp: number; detections: any[] }> = {};
                  decryptedContent.skill_detections.forEach((detection: any) => {
                    const skillId = detection.skill_id || 'unknown';
                    if (!groupedSkills[skillId]) {
                      groupedSkills[skillId] = { total_xp: 0, detections: [] };
                    }
                    groupedSkills[skillId].total_xp += detection.xp_amount || 0;
                    groupedSkills[skillId].detections.push(detection);
                  });

                  return (
                    <div className="space-y-3">
                      {Object.entries(groupedSkills).map(([skillId, data]) => (
                        <div key={skillId} className="border border-glass-border/50 rounded-lg p-4 bg-glass-light/30">
                          {/* Skill Header */}
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span className="text-accent-secondary font-semibold">
                                {getSkillName(skillId)}
                              </span>
                            </div>
                            <span className="text-green-400 font-bold">+{data.total_xp} XP</span>
                          </div>

                          {/* Individual detections */}
                          <div className="space-y-2">
                            {data.detections.map((detection: any, idx: number) => (
                              <div key={idx} className="text-xs bg-bg-tertiary/50 p-2 rounded">
                                <div className="flex items-center justify-between mb-1">
                                  <span className="text-text-tertiary">
                                    🔧 {detection.tool_used || 'Unknown tool'}
                                  </span>
                                  <span className="text-green-400">+{detection.xp_amount} XP</span>
                                </div>
                                <div className="text-text-secondary">{detection.evidence}</div>
                                {detection.tool_details && (
                                  <div className="mt-1 text-text-tertiary text-xs">
                                    {detection.tool_details.query && (
                                      <div>Query: "{detection.tool_details.query.slice(0, 50)}..."</div>
                                    )}
                                    {detection.tool_details.url && (
                                      <div>URL: {detection.tool_details.url.slice(0, 50)}...</div>
                                    )}
                                    {detection.tool_details.prompt && (
                                      <div>Prompt: "{detection.tool_details.prompt.slice(0, 50)}..."</div>
                                    )}
                                    {detection.tool_details.topic && (
                                      <div>Topic: {detection.tool_details.topic}</div>
                                    )}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </GlassCard>
            )}

            {/* Relationship Progression Card - Only for SUMMARY blocks */}
            {selectedBlock.block_type === 'SUMMARY' && decryptedContent?.relationships_affected && Object.keys(decryptedContent.relationships_affected).length > 0 && (
              <GlassCard className="p-6 mb-4">
                <button
                  onClick={() => setRelationshipExpanded(!relationshipExpanded)}
                  className="w-full flex items-center justify-between text-lg font-display text-accent-primary hover:text-accent-primary/80 transition-colors mb-4"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">🤝</span>
                    <span>Relationship Progression</span>
                    <span className="text-sm text-text-tertiary">
                      ({Object.keys(decryptedContent.relationships_affected).length} evaluated)
                    </span>
                  </div>
                  <span className="text-2xl">{relationshipExpanded ? '▼' : '▶'}</span>
                </button>

                {relationshipExpanded && (
                <div className="space-y-4">
                  {Object.entries(decryptedContent.relationships_affected).map(([entityId, evaluation]: [string, any]) => (
                    <div key={entityId} className="border border-glass-border/50 rounded-lg p-4 bg-glass-light/30">
                      {/* Entity Header */}
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span className="text-accent-primary font-semibold">{entityId}</span>
                        </div>
                        <div className="text-xs text-text-tertiary">
                          {evaluation.message_count || 0} messages
                        </div>
                      </div>

                      {/* Evaluation Summary */}
                      {evaluation.evaluation_summary && (
                        <p className="text-sm text-text-secondary mb-3 italic">
                          "{evaluation.evaluation_summary}"
                        </p>
                      )}

                      {/* Deltas Grid */}
                      {evaluation.deltas && Object.keys(evaluation.deltas).length > 0 && (
                        <div className="grid grid-cols-2 gap-2 mb-3">
                          {Object.entries(evaluation.deltas).map(([metric, delta]: [string, any]) => {
                            const deltaNum = typeof delta === 'number' ? delta : 0;
                            const isPositive = deltaNum > 0;
                            const isNegative = deltaNum < 0;

                            return (
                              <div key={metric} className="flex items-center justify-between text-xs">
                                <span className="text-text-tertiary capitalize">{metric}:</span>
                                <span className={`font-semibold ${
                                  isPositive ? 'text-green-400' : isNegative ? 'text-red-400' : 'text-text-tertiary'
                                }`}>
                                  {isPositive ? '+' : ''}{deltaNum.toFixed(1)}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      )}

                      {/* Reasoning */}
                      {evaluation.reasoning && (
                        <details className="mt-3">
                          <summary className="text-xs text-accent-secondary cursor-pointer hover:text-accent-primary transition-colors">
                            View AI Reasoning
                          </summary>
                          <p className="text-xs text-text-secondary mt-2 pl-4 border-l-2 border-accent-secondary/30">
                            {evaluation.reasoning}
                          </p>
                        </details>
                      )}

                      {/* Key Moments */}
                      {evaluation.key_moments && evaluation.key_moments.length > 0 && (
                        <details className="mt-2">
                          <summary className="text-xs text-accent-secondary cursor-pointer hover:text-accent-primary transition-colors">
                            Key Moments ({evaluation.key_moments.length})
                          </summary>
                          <ul className="text-xs text-text-secondary mt-2 pl-4 space-y-1">
                            {evaluation.key_moments.map((moment: string, idx: number) => (
                              <li key={idx} className="list-disc">{moment}</li>
                            ))}
                          </ul>
                        </details>
                      )}
                    </div>
                  ))}
                </div>
                )}
              </GlassCard>
            )}

            {/* Content Card */}
            <GlassCard className="p-6">
              <button
                onClick={() => setContentExpanded(!contentExpanded)}
                className="w-full flex items-center justify-between text-lg font-display text-accent-primary hover:text-accent-primary/80 transition-colors"
              >
                <span>Block Content</span>
                <span className="text-2xl">{contentExpanded ? '▼' : '▶'}</span>
              </button>

              {contentExpanded && (
                <BlockContentViewer
                  blockType={selectedBlock.block_type}
                  content={decryptedContent || selectedBlock.content}
                />
              )}
            </GlassCard>
          </div>
        )}
        </div>
      </div>

      {/* Discard Confirmation Modal */}
      {showDiscardConfirm && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50">
          <GlassCard className="p-6 max-w-md mx-4">
            <h2 className="text-xl font-display text-accent-danger mb-4">
              ⚠️ Discard Session Blocks?
            </h2>

            {/* Show selected block info if applicable */}
            {selectedBlock && selectedBlock.block_number < 0 && (
              <div className="mb-4 p-3 bg-accent-warning/10 border border-accent-warning/30 rounded-lg">
                <div className="text-sm text-text-secondary mb-1">Selected Block:</div>
                <div className="text-sm font-mono text-accent-warning">
                  Block #{selectedBlock.block_number} ({selectedBlock.block_type})
                </div>
              </div>
            )}

            <p className="text-text-primary mb-6">
              {selectedBlock && selectedBlock.block_number < 0 ? (
                <>You can discard the selected session block or all {sessionBlocks.length} session blocks. This action cannot be undone.</>
              ) : (
                <>Are you sure you want to discard all {sessionBlocks.length} session blocks? This action cannot be undone.</>
              )}
            </p>

            <div className="flex gap-3 justify-end">
              <GlassButton
                variant="secondary"
                onClick={cancelDiscard}
              >
                Cancel
              </GlassButton>

              {/* Only show "Discard Selected" if a session block is selected */}
              {selectedBlock && selectedBlock.block_number < 0 && (
                <GlassButton
                  variant="danger"
                  onClick={confirmDiscardSelected}
                  className="bg-accent-warning/20 hover:bg-accent-warning/30 text-accent-warning"
                >
                  Discard Selected
                </GlassButton>
              )}

              <GlassButton
                variant="danger"
                onClick={confirmDiscardAll}
              >
                Discard All
              </GlassButton>
            </div>
          </GlassCard>
        </div>
      )}

      {/* Anchoring Loading Overlay */}
      {isAnchoring && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50">
          <GlassCard className="p-8 max-w-md mx-4">
            <div className="flex flex-col items-center gap-4">
              <div className="text-4xl animate-pulse">⚓</div>
              <h2 className="text-xl font-display text-accent-primary">
                Anchoring Blocks...
              </h2>
              <p className="text-sm text-text-secondary text-center">
                Converting session blocks to permanent blockchain entries.
              </p>
              <div className="w-full bg-glass-light rounded-full h-2 overflow-hidden">
                <div className="h-full bg-accent-primary animate-pulse rounded-full w-full"></div>
              </div>
            </div>
          </GlassCard>
        </div>
      )}

    </div>
  );
};
