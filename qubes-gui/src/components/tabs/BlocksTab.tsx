import { calculateTokenCost, formatUSD, formatBCH } from '../../utils/tokenCostCalculator';
import { formatModelName } from '../../utils/modelFormatter';
import React, { useState, useEffect } from 'react';
import { invoke, convertFileSrc } from '@tauri-apps/api/core';
import { emit } from '@tauri-apps/api/event';
import { GlassCard, GlassButton } from '../glass';
import { Qube } from '../../types';
import { BlockContentViewer } from '../blocks/BlockContentViewer';
import { SKILL_DEFINITIONS } from '../../data/skillDefinitions';
import { ActiveContextPanel, ContextSectionType, ContextSectionData } from '../context';
import { useChainState } from '../../contexts/ChainStateContext';

// Helper to get skill name from ID
const getSkillName = (skillId: string): string => {
  for (const skills of Object.values(SKILL_DEFINITIONS)) {
    const skill = skills.find(s => s.id === skillId);
    if (skill?.name) return skill.name;
  }
  // Fallback: convert ID to title case
  return skillId.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
};

// Category icons for skills
const CATEGORY_ICONS: Record<string, string> = {
  'ai_reasoning': '🧠',
  'social_intelligence': '🤝',
  'technical_expertise': '💻',
  'creative_expression': '🎨',
  'knowledge_domains': '📚',
  'security_privacy': '🛡️',
  'games': '🎮'
};

// Tier icons for skills
const TIER_ICONS: Record<string, string> = {
  'sun': '☀️',
  'planet': '🪐',
  'moon': '🌙'
};

// Helper to format voice model names: "openai:fable" -> "OpenAI - Fable"
const formatVoiceName = (voiceId: string): string => {
  if (!voiceId) return 'None';

  const PROVIDER_NAMES: Record<string, string> = {
    openai: 'OpenAI',
    google: 'Google',
    gemini: 'Gemini',
    elevenlabs: 'ElevenLabs',
  };

  if (voiceId.includes(':')) {
    const [provider, voice] = voiceId.split(':');
    const providerName = PROVIDER_NAMES[provider.toLowerCase()] || (provider.charAt(0).toUpperCase() + provider.slice(1));
    const voiceName = voice.charAt(0).toUpperCase() + voice.slice(1);
    return `${providerName} - ${voiceName}`;
  }
  return voiceId.charAt(0).toUpperCase() + voiceId.slice(1);
};

// Expandable skill category component
const ExpandableSkillCategory: React.FC<{ category: any }> = ({ category }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const categoryIcon = CATEGORY_ICONS[category.category_id] || '⚡';

  // Get skills that have XP > 0 for the preview
  const skillsWithXP = (category.skills || []).filter((s: any) => s.xp > 0);
  const xpPreview = skillsWithXP.length > 0
    ? skillsWithXP.slice(0, 3).map((s: any) => `${getSkillName(s.skill_id) || s.name}: ${s.xp}`).join(', ')
    : null;

  return (
    <div className="bg-glass-bg/30 rounded-lg overflow-hidden">
      {/* Category Header - clickable to expand */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex flex-col p-3 hover:bg-glass-bg/50 transition-colors text-left"
      >
        <div className="flex items-center justify-between w-full">
          <span className="text-text-primary font-medium flex items-center gap-2">
            <span>{categoryIcon}</span>
            {category.category_name}
            <span className="text-xs text-text-tertiary">({category.skills?.length || 0} skills)</span>
          </span>
          <div className="flex items-center gap-3">
            <span className="text-accent-primary text-sm">{category.total_xp} XP</span>
            <span className="text-text-tertiary text-xs">{isExpanded ? '▼' : '▶'}</span>
          </div>
        </div>
        {/* XP breakdown preview - shows which skills contributed */}
        {xpPreview && !isExpanded && (
          <div className="text-xs text-text-tertiary mt-1 ml-6">
            {xpPreview}{skillsWithXP.length > 3 ? ` +${skillsWithXP.length - 3} more` : ''}
          </div>
        )}
      </button>

      {/* Expanded Skills List */}
      {isExpanded && category.skills && (
        <div className="border-t border-glass-border">
          {category.skills.map((skill: any, idx: number) => (
            <div
              key={skill.skill_id || idx}
              className={`flex items-center justify-between px-4 py-2 text-sm ${
                idx % 2 === 0 ? 'bg-glass-bg/10' : ''
              } ${!skill.unlocked ? 'opacity-50' : ''}`}
            >
              <span className="flex items-center gap-2">
                <span className="text-xs">{TIER_ICONS[skill.tier] || '🌙'}</span>
                <span className={skill.unlocked ? 'text-text-primary' : 'text-text-tertiary'}>
                  {getSkillName(skill.skill_id) || skill.name}
                </span>
                {skill.tool_unlock && (
                  <span className="text-xs px-1.5 py-0.5 bg-purple-500/20 text-purple-400 rounded" title={`Unlocks: ${skill.tool_unlock}`}>
                    🔧
                  </span>
                )}
                {!skill.unlocked && (
                  <span className="text-xs text-text-tertiary">🔒</span>
                )}
              </span>
              <div className="flex items-center gap-3 text-xs">
                <span className="text-accent-primary">Lv {skill.level}</span>
                <span className="text-text-tertiary w-16 text-right">{skill.xp} XP</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
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
  onQubesChange?: () => void;
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

export const BlocksTab: React.FC<BlocksTabProps> = ({ selectedQubes, userId, password, isActive = false, onQubesChange }) => {
  const [sessionBlocks, setSessionBlocks] = useState<Block[]>([]);
  const [permanentBlocks, setPermanentBlocks] = useState<Block[]>([]);

  // Track if initial load has completed for this qube
  // This prevents the tab switch effect from running before initial data is loaded
  const hasInitiallyLoaded = React.useRef(false);

  // Track the qube ID that was loaded - used to detect when we need a fresh load
  const loadedQubeId = React.useRef<string | null>(null);
  const [selectedBlock, setSelectedBlock] = useState<Block | null>(null);
  const [selectedSection, setSelectedSection] = useState<SelectionSection | null>(null);
  // Multi-select state for session blocks
  const [selectedSessionBlocks, setSelectedSessionBlocks] = useState<Set<number>>(new Set());
  const [lastClickedSessionBlock, setLastClickedSessionBlock] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [decryptedContent, setDecryptedContent] = useState<any>(null);
  const [showDiscardConfirm, setShowDiscardConfirm] = useState(false);
  const [showAnchorConfirm, setShowAnchorConfirm] = useState(false);
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

  // Sub-section collapse states (all collapsed by default)
  const [currentSessionExpanded, setCurrentSessionExpanded] = useState(false);
  const [recentHistoryExpanded, setRecentHistoryExpanded] = useState(false);
  const [recalledMemoriesExpanded, setRecalledMemoriesExpanded] = useState(false);

  // Sort order state (true = newest first, false = oldest first)
  const [shortTermNewestFirst, setShortTermNewestFirst] = useState(true);
  const [longTermNewestFirst, setLongTermNewestFirst] = useState(true);

  // Context section selection (for right panel display)
  const [selectedContextSection, setSelectedContextSection] = useState<ContextSectionData | null>(null);

  // Owner info section collapsed states (both default to collapsed)
  const [ownerInfoPrivateExpanded, setOwnerInfoPrivateExpanded] = useState(false);
  const [ownerInfoPublicExpanded, setOwnerInfoPublicExpanded] = useState(false);
  // Track which categories are expanded (default all collapsed)
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

  // Context preview state
  const [contextPreview, setContextPreview] = useState<any>(null);
  const [contextLoading, setContextLoading] = useState(false);
  const [showContextPanels, setShowContextPanels] = useState(true);

  // Use global chain state cache
  const { loadChainState, getChainState, isLoading: isChainStateLoading, cacheVersion } = useChainState();

  const selectedQube = selectedQubes.length === 1 ? selectedQubes[0] : null;

  // Reset expanded states when switching blocks (auto-expand Block Content)
  useEffect(() => {
    setCryptoExpanded(false);
    setContentExpanded(true); // Auto-expand Block Content when block is selected
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
  const copyToClipboard = async (text: string, _label: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const loadBlocks = async (): Promise<{ sessionCount: number; permanentCount: number } | null> => {
    if (!selectedQube) return null;

    setLoading(true);
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

      if (result.success) {
        const sessionCount = result.session_blocks?.length || 0;
        const permanentCount = result.permanent_blocks?.length || 0;
        setSessionBlocks(result.session_blocks || []);
        setPermanentBlocks(result.permanent_blocks || []);

        // Reset pagination when blocks are loaded
        setSessionBlocksToShow(10);
        setPermanentBlocksToShow(10);
        // Clear multi-select state when blocks are reloaded
        setSelectedSessionBlocks(new Set());
        setLastClickedSessionBlock(null);
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

  // Load context preview using global chain state cache
  const loadContextPreview = async (forceRefresh = false) => {
    if (!selectedQube) return;

    const qubeId = selectedQube.qube_id;

    // Get cached data immediately for instant display
    const cached = getChainState(qubeId);
    if (cached && !forceRefresh) {
      setContextPreview({
        active_context: cached.active_context,
        short_term_memory: cached.short_term_memory,
      });
    }

    // Only show loading if we don't have cached data
    if (!cached) {
      setContextLoading(true);
    }

    try {
      const data = await loadChainState(qubeId, forceRefresh);
      if (data) {
        setContextPreview({
          active_context: data.active_context,
          short_term_memory: data.short_term_memory,
        });
      }
    } catch (error) {
      console.warn('Failed to load context preview:', error);
      if (!cached) {
        setContextPreview(null);
      }
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
    setSelectedContextSection(null);  // Clear right panel selection
    hasInitiallyLoaded.current = false;
    loadedQubeId.current = null;

    // Use cached context preview from global cache if available for instant display
    if (currentQubeId) {
      const cached = getChainState(currentQubeId);
      if (cached) {
        setContextPreview({
          active_context: cached.active_context,
          short_term_memory: cached.short_term_memory,
        });
      } else {
        setContextPreview(null);
      }
    } else {
      setContextPreview(null);
    }

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

  // Helper to get section data from context preview
  const getSectionDataFromPreview = (preview: any, sectionType: ContextSectionType): any => {
    if (!preview) return null;
    const ac = preview.active_context;
    const stm = preview.short_term_memory;

    switch (sectionType) {
      case 'identity': return ac?.genesis_identity;
      case 'stats': return ac?.stats;
      case 'session': return { ...ac?.session, blocks: stm?.session };
      case 'settings': return ac?.settings;
      case 'relationships': return ac?.relationships;
      case 'skills': return ac?.skills;
      case 'financial': return ac?.wallet;
      case 'mood': return ac?.mood;
      case 'health': return ac?.health;
      case 'owner_info': return ac?.owner_info;
      case 'recalled': return stm?.semantic_recalls;
      case 'history': return stm?.recent_permanent;
      case 'chain': return ac?.chain;
      default: return null;
    }
  };

  // Reload blocks and sync context when tab becomes active or cache is updated
  // This ensures new blocks created in Chat are visible when switching to Blocks tab
  // and settings changes on other tabs are reflected here
  useEffect(() => {
    if (isActive && selectedQube && hasInitiallyLoaded.current && loadedQubeId.current === selectedQube.qube_id) {
      // Tab became active or cache was updated and we already have data for this qube - refresh it
      loadBlocks();
      // Sync from global cache (context handles periodic refresh)
      const cached = getChainState(selectedQube.qube_id);
      if (cached) {
        const newPreview = {
          active_context: cached.active_context,
          short_term_memory: cached.short_term_memory,
        };
        setContextPreview(newPreview);

        // Also refresh the selected section data if one is selected
        if (selectedContextSection) {
          const updatedData = getSectionDataFromPreview(newPreview, selectedContextSection.type);
          if (updatedData) {
            setSelectedContextSection({
              ...selectedContextSection,
              data: updatedData,
            });
          }
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isActive, cacheVersion]);

  const handleAnchorClick = () => {
    if (!selectedQube || sessionBlocks.length === 0) return;
    setShowAnchorConfirm(true);
  };

  const confirmAnchor = async () => {
    if (!selectedQube) return;

    setShowAnchorConfirm(false);
    setIsAnchoring(true);
    try {
      await invoke('anchor_session', {
        userId,
        qubeId: selectedQube.qube_id,
        password,
      });
      await loadBlocks();
      // Force refresh context preview since blocks changed
      await loadContextPreview(true);
      // Refresh qubes list to update chain_length on cards
      onQubesChange?.();
    } catch (error) {
      console.error('Failed to anchor session:', error);
      alert(`Failed to anchor session: ${error}`);
    } finally {
      setIsAnchoring(false);
    }
  };

  const cancelAnchor = () => {
    setShowAnchorConfirm(false);
  };

  const handleDiscardClick = () => {
    if (!selectedQube || sessionBlocks.length === 0) return;
    setShowDiscardConfirm(true);
  };

  const confirmDiscardAll = async () => {
    if (!selectedQube) return;

    setShowDiscardConfirm(false);

    try {
      const result = await invoke<{ success: boolean; blocks_discarded: number; current_model?: string }>('discard_session', {
        userId,
        qubeId: selectedQube.qube_id,
        password,
      });
      await loadBlocks();
      // Refresh context preview since blocks changed
      await loadContextPreview();
      setSelectedBlock(null);
      setSelectedSection(null);
      setSelectedSessionBlocks(new Set());
      setLastClickedSessionBlock(null);

      // Sync frontend model state with backend after discard
      // This fixes the issue where model switches during the discarded session
      // leave the frontend showing the wrong model
      if (result.current_model) {
        emit('qube-model-changed', {
          qubeId: selectedQube.qube_id,
          newModel: result.current_model,
        });
      }
    } catch (error) {
      console.error('Failed to discard session:', error);
      alert(`Failed to discard session: ${error}`);
    }
  };

  const confirmDiscardSelected = async () => {
    if (!selectedQube) return;

    // Determine which blocks to delete - collect both block_number and timestamp
    // Timestamps are stable identifiers that don't change between delete calls,
    // unlike block_numbers which get re-indexed when the session reloads.
    const blocksToDelete: { blockNumber: number; timestamp: number }[] = [];

    if (selectedSessionBlocks.size > 0) {
      // Multi-select mode: find all selected blocks and get their timestamps
      for (const blockNum of selectedSessionBlocks) {
        const block = sessionBlocks.find(b => b.block_number === blockNum);
        if (block) {
          blocksToDelete.push({ blockNumber: block.block_number, timestamp: block.timestamp });
        }
      }
    } else if (selectedBlock && selectedBlock.block_number < 0) {
      // Single selection mode: use the selected block
      blocksToDelete.push({ blockNumber: selectedBlock.block_number, timestamp: selectedBlock.timestamp });
    } else {
      alert('Only session blocks can be discarded individually.');
      return;
    }

    // Sort doesn't matter anymore since we use timestamps for deletion,
    // but keep for consistency in logging/display
    blocksToDelete.sort((a, b) => a.blockNumber - b.blockNumber);

    setShowDiscardConfirm(false);

    try {
      // Delete blocks one by one using timestamps for stable identification
      for (const { blockNumber, timestamp } of blocksToDelete) {
        await invoke('delete_session_block', {
          userId,
          qubeId: selectedQube.qube_id,
          blockNumber,
          password,
          timestamp,  // Pass timestamp for stable deletion
        });
      }
      await loadBlocks();
      // Refresh context preview since blocks changed
      await loadContextPreview();
      setSelectedBlock(null);
      setSelectedSection(null);
      setSelectedSessionBlocks(new Set());
      setLastClickedSessionBlock(null);
    } catch (error) {
      console.error('Failed to discard block(s):', error);
      alert(`Failed to discard block(s): ${error}`);
    }
  };

  const cancelDiscard = () => {
    setShowDiscardConfirm(false);
  };

  const handleBlockClick = (block: Block, section: SelectionSection, event?: React.MouseEvent) => {
    try {
      // Handle multi-select for session blocks only
      if (section === 'session' && event && (event.ctrlKey || event.metaKey || event.shiftKey)) {
        // Prevent text selection on shift+click
        if (event.shiftKey) {
          event.preventDefault();
        }
        const blockNum = block.block_number;

        if (event.shiftKey && lastClickedSessionBlock !== null) {
          // Shift+click: select range from last clicked to current
          // Session blocks have negative numbers, more negative = newer
          const start = Math.min(lastClickedSessionBlock, blockNum);
          const end = Math.max(lastClickedSessionBlock, blockNum);

          // Find all session blocks in the range
          const blocksInRange = sessionBlocks
            .filter(b => b.block_number >= start && b.block_number <= end)
            .map(b => b.block_number);

          setSelectedSessionBlocks(prev => {
            const next = new Set(prev);
            // If this is the first multi-select and we have a previously selected block, include it
            if (next.size === 0 && lastClickedSessionBlock !== null) {
              next.add(lastClickedSessionBlock);
            }
            blocksInRange.forEach(num => next.add(num));
            return next;
          });
        } else if (event.ctrlKey || event.metaKey) {
          // Ctrl+click (or Cmd+click on Mac): toggle individual block
          setSelectedSessionBlocks(prev => {
            const next = new Set(prev);
            // If this is the first ctrl+click and we have a previously selected block, include it
            if (next.size === 0 && lastClickedSessionBlock !== null && lastClickedSessionBlock !== blockNum) {
              next.add(lastClickedSessionBlock);
            }
            // Toggle the clicked block
            if (next.has(blockNum)) {
              next.delete(blockNum);
            } else {
              next.add(blockNum);
            }
            return next;
          });
        }

        setLastClickedSessionBlock(blockNum);
        // For multi-select, also set the clicked block as the "primary" selected block for display
        setSelectedBlock(block);
        setSelectedSection(section);
        setSelectedContextSection(null);
        setDecryptedContent(block.content);
        setContentExpanded(true); // Auto-expand Block Content when block is clicked
        return;
      }

      // Normal click: clear multi-select and select single block
      setSelectedSessionBlocks(new Set());
      setLastClickedSessionBlock(section === 'session' ? block.block_number : null);
      setSelectedBlock(block);
      setSelectedSection(section);
      // Clear context section selection when selecting a block
      setSelectedContextSection(null);
      // All blocks are already decrypted since we prompted for password on load
      setDecryptedContent(block.content);
      setContentExpanded(true); // Auto-expand Block Content when block is clicked
    } catch (error) {
      console.error('Error setting selected block:', error);
      alert(`Error displaying block: ${error}`);
    }
  };

  const filteredPermanentBlocks = permanentBlocks.filter(block => {
    const matchesSearch = searchQuery === '' ||
      JSON.stringify(block).toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = filterType === 'all' || block.block_type === filterType;
    return matchesSearch && matchesFilter;
  });

  // Sort blocks by block number (negative = session, positive = permanent)
  // For session blocks: -1 is oldest, -12 is newest (more negative = newer)
  // For permanent blocks: 0 is oldest, higher = newer
  const sortedSessionBlocks = [...sessionBlocks].sort((a, b) =>
    shortTermNewestFirst ? a.block_number - b.block_number : b.block_number - a.block_number
  );

  const sortedPermanentBlocks = [...filteredPermanentBlocks].sort((a, b) =>
    longTermNewestFirst ? b.block_number - a.block_number : a.block_number - b.block_number
  );

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
                    await loadContextPreview(true); // Force refresh on manual click
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
                selectedSection={selectedContextSection?.type}
                onSectionSelect={(section) => {
                  setSelectedContextSection(section);
                  // Clear block selection when selecting a context section
                  if (section) {
                    setSelectedBlock(null);
                    setSelectedSection(null);
                  }
                }}
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
              <h2 className="text-lg font-display text-amber-400 flex items-center gap-2">
                <span className="text-2xl">🧠</span>
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
                {shortTermExpanded && (
                  <span
                    onClick={(e) => { e.stopPropagation(); setShortTermNewestFirst(!shortTermNewestFirst); }}
                    className="text-xs text-text-secondary hover:text-amber-400 transition-colors cursor-pointer"
                    title={shortTermNewestFirst ? 'Showing newest first' : 'Showing oldest first'}
                  >
                    {shortTermNewestFirst ? '↓ New' : '↑ Old'}
                  </span>
                )}
                <span className="text-text-tertiary">{shortTermExpanded ? '▼' : '▶'}</span>
              </div>
            </button>

            {shortTermExpanded && (
              <div className="mt-4">
            {/* Anchor/Discard buttons at top of Short-term Memory */}
            {sessionBlocks.length > 0 && (
              <div className="flex gap-2 mb-3 mt-6">
                <GlassButton
                  variant="primary"
                  onClick={handleAnchorClick}
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
            )}

            {/* Session Blocks (Current Session) - shown first as most relevant */}
            {sessionBlocks.length > 0 ? (
              <>
                <button
                  onClick={() => setCurrentSessionExpanded(!currentSessionExpanded)}
                  className={`w-full text-left text-sm font-semibold ${SECTION_COLORS.session.text} mb-2 flex items-center gap-2 p-2 rounded hover:bg-glass-bg/30 transition-colors`}
                >
                  <span className="text-base">{currentSessionExpanded ? '▼' : '▶'}</span>
                  <span className="text-lg">⚡</span>
                  <span>Current Session</span>
                  <span className={`${SECTION_COLORS.session.bg} ${SECTION_COLORS.session.text} px-2 py-0.5 rounded text-xs font-normal`}>
                    {sessionBlocks.length}
                  </span>
                </button>

                {currentSessionExpanded && (
                  <>
                    {/* Multi-select hint */}
                    {sessionBlocks.length > 1 && (
                      <div className="text-xs text-text-tertiary mb-2 italic ml-2">
                        Tip: Ctrl+click to select multiple, Shift+click for range
                      </div>
                    )}

                    <div className="space-y-2">
                  {sortedSessionBlocks.slice(0, sessionBlocksToShow).map((block) => {
                    const isMultiSelected = selectedSessionBlocks.has(block.block_number);
                    const isPrimarySelected = selectedBlock?.block_number === block.block_number && selectedSection === 'session';

                    return (
                      <GlassCard
                        key={block.block_number}
                        variant="interactive"
                        className={`p-3 cursor-pointer border-l-2 ${getBlockTypeBorder(block.block_type)} border border-dashed ${SECTION_COLORS.session.border}/30 bg-sky-400/5 select-none ${
                          isPrimarySelected
                            ? `ring-2 ${getBlockTypeRing(block.block_type)}`
                            : isMultiSelected
                            ? 'ring-2 ring-accent-warning bg-accent-warning/10'
                            : ''
                        }`}
                        onMouseDown={(e) => { if (e.shiftKey) e.preventDefault(); }}
                        onClick={(e) => handleBlockClick(block, 'session', e)}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className={`text-sm font-mono ${SECTION_COLORS.session.text} flex items-center gap-2`}>
                            {isMultiSelected && (
                              <span className="text-accent-warning">✓</span>
                            )}
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
                    );
                  })}
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
                )}
              </>
            ) : (
              <div className={`text-center py-8 text-text-tertiary text-sm border-2 border-dashed ${SECTION_COLORS.session.border}/20 rounded-lg`}>
                No session blocks - start a conversation to create short-term memories
              </div>
            )}

            {/* Recent History from Context */}
            {contextPreview?.short_term_memory?.recent_permanent?.blocks?.length > 0 && (
              <div className="mb-3 mt-3">
                <button
                  onClick={() => setRecentHistoryExpanded(!recentHistoryExpanded)}
                  className={`w-full text-left text-sm font-semibold ${SECTION_COLORS.recent.text} mb-2 flex items-center gap-2 p-2 rounded hover:bg-glass-bg/30 transition-colors`}
                >
                  <span className="text-base">{recentHistoryExpanded ? '▼' : '▶'}</span>
                  <span className="text-lg">📚</span>
                  <span>Recent History</span>
                  <span className={`${SECTION_COLORS.recent.bg} ${SECTION_COLORS.recent.text} px-2 py-0.5 rounded text-xs font-normal`}>
                    {contextPreview.short_term_memory.recent_permanent.count}
                  </span>
                </button>
                {recentHistoryExpanded && (
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
                        {block.timestamp
                          ? new Date(block.timestamp > 1e12 ? block.timestamp : block.timestamp * 1000).toLocaleString()
                          : 'No timestamp'}
                      </div>
                    </GlassCard>
                  ))}
                  </div>
                )}
              </div>
            )}

            {/* Recalled Memories from Context */}
            {contextPreview?.short_term_memory?.semantic_recalls?.blocks?.length > 0 && (
              <div className="mb-3">
                <button
                  onClick={() => setRecalledMemoriesExpanded(!recalledMemoriesExpanded)}
                  className={`w-full text-left text-sm font-semibold ${SECTION_COLORS.recalled.text} mb-2 flex items-center gap-2 p-2 rounded hover:bg-glass-bg/30 transition-colors`}
                >
                  <span className="text-base">{recalledMemoriesExpanded ? '▼' : '▶'}</span>
                  <span className="text-lg">🔮</span>
                  <span>Recalled Memories</span>
                  <span className={`${SECTION_COLORS.recalled.bg} ${SECTION_COLORS.recalled.text} px-2 py-0.5 rounded text-xs font-normal`}>
                    {contextPreview.short_term_memory.semantic_recalls.count}
                  </span>
                </button>
                {recalledMemoriesExpanded && (
                  <div className="space-y-2">
                  {contextPreview.short_term_memory.semantic_recalls.blocks.map((block: any, idx: number) => {
                    // Handle relevance score - cap at 100%, handle values > 1 (already percentages)
                    const rawScore = block.relevance_score || 0;
                    const relevancePercent = rawScore > 1 ? Math.min(Math.round(rawScore), 100) : Math.min(Math.round(rawScore * 100), 100);

                    return (
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
                              {relevancePercent}% match
                            </span>
                            <span className={`text-xs px-2 py-0.5 rounded ${getBlockTypeColor(block.block_type)}`}>
                              {block.block_type}
                            </span>
                          </div>
                        </div>
                        <div className="text-xs text-text-tertiary">
                          {block.timestamp
                            ? new Date(block.timestamp > 1e12 ? block.timestamp : block.timestamp * 1000).toLocaleString()
                            : 'No timestamp'}
                        </div>
                      </GlassCard>
                    );
                  })}
                  </div>
                )}
              </div>
            )}
              </div>
            )}
          </GlassCard>

          {/* Long-term Memory (Permanent Blocks) */}
          <GlassCard className="p-3 mb-4 border-l-2 border-l-cyan-400">
            <button
              onClick={() => setLongTermExpanded(!longTermExpanded)}
              className="w-full flex items-center justify-between"
            >
              <h2 className="text-lg font-display text-cyan-400 flex items-center gap-2">
                <span className="text-2xl">💾</span>
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
                {longTermExpanded && (
                  <span
                    onClick={(e) => { e.stopPropagation(); setLongTermNewestFirst(!longTermNewestFirst); }}
                    className="text-xs text-text-secondary hover:text-cyan-400 transition-colors cursor-pointer"
                    title={longTermNewestFirst ? 'Showing newest first' : 'Showing oldest first'}
                  >
                    {longTermNewestFirst ? '↓ New' : '↑ Old'}
                  </span>
                )}
                <span className="text-text-tertiary">{longTermExpanded ? '▼' : '▶'}</span>
              </div>
            </button>

            {longTermExpanded && (
              <div className="mt-4">
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
                  {sortedPermanentBlocks.slice(0, permanentBlocksToShow).map((block) => (
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

                  {sortedPermanentBlocks.length > permanentBlocksToShow && (
                    <div className="mt-3 text-center">
                      <button
                        onClick={() => setPermanentBlocksToShow(prev => Math.min(prev + 10, sortedPermanentBlocks.length))}
                        className="text-sm text-text-secondary hover:text-text-primary transition-colors px-4 py-2 rounded bg-glass-bg/30 hover:bg-glass-bg/50"
                      >
                        Show More ({sortedPermanentBlocks.length - permanentBlocksToShow} remaining)
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
              </div>
            )}
          </GlassCard>
        </div>
      </div>

      {/* Right Panel - Block/Context Detail Viewer */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-6">
        {selectedContextSection ? (
          /* Context Section Detail View */
          <div className="space-y-4 max-w-4xl">
            <GlassCard className="p-6">
              <h2 className="text-xl font-display text-accent-primary mb-4 flex items-center gap-2">
                <span className="text-2xl">{selectedContextSection.icon}</span>
                {selectedContextSection.title}
              </h2>

              {/* Owner Info */}
              {selectedContextSection.type === 'owner_info' && (
                <div className="space-y-3">
                  {selectedContextSection.data && selectedContextSection.data.total_fields > 0 ? (
                    (() => {
                      // Separate fields by sensitivity
                      const allFields = selectedContextSection.data.top_fields || [];
                      const privateFields = allFields.filter((f: any) => f.sensitivity === 'private' || f.sensitivity === 'secret');
                      const publicFields = allFields.filter((f: any) => f.sensitivity === 'public');

                      // Category display info - distinct colors that don't clash with Private (yellow) or Public (emerald)
                      const categoryInfo: Record<string, { icon: string; label: string; color: string; bg: string }> = {
                        standard: { icon: '📋', label: 'Basic Info', color: 'text-slate-300', bg: 'bg-slate-500/15' },
                        physical: { icon: '🏠', label: 'Physical', color: 'text-orange-400', bg: 'bg-orange-500/15' },
                        preferences: { icon: '⭐', label: 'Preferences', color: 'text-fuchsia-400', bg: 'bg-fuchsia-500/15' },
                        people: { icon: '👥', label: 'People', color: 'text-cyan-400', bg: 'bg-cyan-500/15' },
                        dates: { icon: '📅', label: 'Important Dates', color: 'text-rose-400', bg: 'bg-rose-500/15' },
                        dynamic: { icon: '✨', label: 'Other', color: 'text-indigo-400', bg: 'bg-indigo-500/15' },
                      };

                      // Group fields by category
                      const groupByCategory = (fields: any[]) => {
                        const groups: Record<string, any[]> = {};
                        fields.forEach((f: any) => {
                          const cat = f.category || 'dynamic';
                          if (!groups[cat]) groups[cat] = [];
                          groups[cat].push(f);
                        });
                        return groups;
                      };

                      // Render a field row with stacked layout
                      const renderField = (field: any, idx: number, isPrivate: boolean) => (
                        <div key={idx} className="py-2 px-3 bg-glass-bg/30 rounded-lg">
                          <div className="text-xs text-text-tertiary capitalize mb-1">
                            {field.key.replace(/_/g, ' ')}
                          </div>
                          <div className={`text-sm ${isPrivate ? 'text-yellow-300' : 'text-text-primary'}`}>
                            {field.value}
                          </div>
                        </div>
                      );

                      // Render fields grouped by category (collapsible)
                      const renderGroupedFields = (fields: any[], isPrivate: boolean) => {
                        const grouped = groupByCategory(fields);
                        const categoryOrder = ['standard', 'physical', 'preferences', 'people', 'dates', 'dynamic'];

                        return categoryOrder
                          .filter(cat => grouped[cat] && grouped[cat].length > 0)
                          .map(cat => {
                            const catInfo = categoryInfo[cat] || { icon: '📌', label: cat, color: 'text-text-tertiary', bg: 'bg-glass-bg/20' };
                            const isExpanded = expandedCategories.has(cat);

                            return (
                              <div key={cat} className="mb-2 last:mb-0 rounded-lg overflow-hidden border border-glass-border/20">
                                <button
                                  onClick={() => toggleCategory(cat)}
                                  className={`w-full flex items-center justify-between p-2 ${catInfo.bg} hover:brightness-110 transition-all`}
                                >
                                  <span className={`text-sm font-medium flex items-center gap-2 ${catInfo.color}`}>
                                    <span>{catInfo.icon}</span>
                                    <span>{catInfo.label}</span>
                                    <span className="text-xs opacity-60">({grouped[cat].length})</span>
                                  </span>
                                  <span className={`text-xs ${catInfo.color}`}>
                                    {isExpanded ? '▼' : '▶'}
                                  </span>
                                </button>
                                {isExpanded && (
                                  <div className="p-2 space-y-2">
                                    {grouped[cat].map((field: any, idx: number) => renderField(field, idx, isPrivate))}
                                  </div>
                                )}
                              </div>
                            );
                          });
                      };

                      return (
                        <div className="space-y-4">
                          {/* Private Section (on top, collapsible) */}
                          <div className="border border-yellow-500/30 rounded-lg overflow-hidden">
                            <button
                              onClick={() => setOwnerInfoPrivateExpanded(!ownerInfoPrivateExpanded)}
                              className="w-full flex items-center justify-between p-3 bg-yellow-500/10 hover:bg-yellow-500/20 transition-colors"
                            >
                              <span className="flex items-center gap-2 text-yellow-400 font-medium">
                                <span>🔒</span>
                                Private
                                <span className="text-xs bg-yellow-500/20 px-2 py-0.5 rounded">
                                  {selectedContextSection.data.private_fields + (selectedContextSection.data.secret_fields || 0)} fields
                                </span>
                              </span>
                              <span className="text-yellow-400 text-xs">
                                {ownerInfoPrivateExpanded ? '▼' : '▶'}
                              </span>
                            </button>
                            {ownerInfoPrivateExpanded && (
                              <div className="p-4 bg-glass-bg/20">
                                {privateFields.length > 0 ? (
                                  renderGroupedFields(privateFields, true)
                                ) : (
                                  <div className="text-text-tertiary text-sm text-center py-2">
                                    No private fields stored yet
                                  </div>
                                )}
                              </div>
                            )}
                          </div>

                          {/* Public Section (collapsible) */}
                          <div className="border border-emerald-500/30 rounded-lg overflow-hidden">
                            <button
                              onClick={() => setOwnerInfoPublicExpanded(!ownerInfoPublicExpanded)}
                              className="w-full flex items-center justify-between p-3 bg-emerald-500/10 hover:bg-emerald-500/20 transition-colors"
                            >
                              <span className="flex items-center gap-2 text-emerald-400 font-medium">
                                <span>🌐</span>
                                Public
                                <span className="text-xs bg-emerald-500/20 px-2 py-0.5 rounded">
                                  {selectedContextSection.data.public_fields} fields
                                </span>
                              </span>
                              <span className="text-emerald-400 text-xs">
                                {ownerInfoPublicExpanded ? '▼' : '▶'}
                              </span>
                            </button>
                            {ownerInfoPublicExpanded && (
                              <div className="p-4 bg-glass-bg/20">
                                {publicFields.length > 0 ? (
                                  renderGroupedFields(publicFields, false)
                                ) : (
                                  <div className="text-text-tertiary text-sm text-center py-2">
                                    No public fields stored yet
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })()
                  ) : (
                    <div className="text-text-tertiary p-4 bg-glass-bg/20 rounded-lg text-center">
                      <div className="text-4xl mb-2">👤</div>
                      <p>No owner info recorded yet.</p>
                      <p className="text-sm mt-1">Chat with your Qube and share personal details - they'll remember!</p>
                    </div>
                  )}
                </div>
              )}

              {/* Genesis Identity (type: 'identity' or legacy 'genesis') */}
              {(selectedContextSection.type === 'genesis' || selectedContextSection.type === 'identity') && selectedContextSection.data && (
                <div className="space-y-4">
                  {/* Qube Name */}
                  <div className="flex items-center gap-3 pb-3 border-b border-glass-border">
                    <span className="text-3xl">🤖</span>
                    <div>
                      <h3 className="text-xl font-display text-text-primary">{selectedContextSection.data.name}</h3>
                      <span className="text-text-tertiary text-sm">Sovereign AI Entity</span>
                    </div>
                  </div>

                  {/* Genesis Prompt */}
                  <div>
                    <span className="text-text-tertiary text-sm">Genesis Prompt:</span>
                    <div className="mt-2 p-3 bg-glass-bg/30 rounded-lg text-text-secondary text-sm">
                      {selectedContextSection.data.genesis_prompt}
                    </div>
                  </div>

                  {/* Configuration */}
                  <div className="p-3 bg-glass-bg/20 rounded-lg border border-glass-border">
                    <div className="text-text-tertiary text-xs uppercase tracking-wider mb-3">Configuration</div>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <span className="text-text-tertiary">Qube ID</span>
                        <div className="text-text-primary font-mono text-xs mt-1">{selectedContextSection.data.qube_id}</div>
                      </div>
                      <div>
                        <span className="text-text-tertiary">AI Provider</span>
                        <div className="text-text-primary mt-1">{selectedContextSection.data.ai_provider || 'Unknown'}</div>
                      </div>
                      <div>
                        <span className="text-text-tertiary">AI Model</span>
                        <div className="text-text-primary mt-1">{selectedContextSection.data.ai_model}</div>
                      </div>
                      <div>
                        <span className="text-text-tertiary">Voice</span>
                        <div className="text-text-primary mt-1">{formatVoiceName(selectedContextSection.data.voice_model)}</div>
                      </div>
                    </div>
                  </div>

                  {/* Network (if NFT minted) */}
                  {selectedContextSection.data.nft_category_id && (
                    <div className="p-3 bg-glass-bg/20 rounded-lg border border-glass-border">
                      <div className="flex items-center gap-2 mb-3">
                        <span className="text-text-tertiary text-xs uppercase tracking-wider">Network</span>
                        <span className="text-xs px-2 py-0.5 bg-emerald-500/20 text-emerald-400 rounded-full border border-emerald-500/30">
                          NFT Minted
                        </span>
                      </div>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-text-tertiary">Blockchain</span>
                          <span className="text-text-primary flex items-center gap-1">
                            <span className="text-emerald-400">●</span>
                            {selectedContextSection.data.blockchain || 'Bitcoin Cash'}
                          </span>
                        </div>
                        {selectedContextSection.data.qube_wallet_address && (
                          <div>
                            <span className="text-text-tertiary">Qube Wallet</span>
                            <div className="text-text-primary font-mono text-xs mt-1 break-all">
                              {selectedContextSection.data.qube_wallet_address}
                            </div>
                          </div>
                        )}
                        <div>
                          <span className="text-text-tertiary">Category</span>
                          <div className="text-text-primary font-mono text-xs mt-1 break-all">
                            {selectedContextSection.data.nft_category_id}
                          </div>
                        </div>
                        {selectedContextSection.data.mint_txid && (
                          <div>
                            <span className="text-text-tertiary">Mint TX</span>
                            <div className="text-text-primary font-mono text-xs mt-1 break-all">
                              {selectedContextSection.data.mint_txid}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Tools */}
                  {selectedContextSection.data.available_tools && selectedContextSection.data.available_tools.length > 0 && (
                    <div className="p-3 bg-glass-bg/20 rounded-lg border border-glass-border">
                      <div className="text-text-tertiary text-xs uppercase tracking-wider mb-3">
                        Tools ({selectedContextSection.data.available_tools.length} available)
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {selectedContextSection.data.available_tools.map((tool: string, idx: number) => (
                          <span
                            key={idx}
                            className="text-xs px-2 py-1 bg-accent-primary/20 text-accent-primary rounded border border-accent-primary/30"
                          >
                            {tool.replace(/_/g, ' ')}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Relationships */}
              {selectedContextSection.type === 'relationships' && (
                <div className="space-y-3">
                  {selectedContextSection.data?.top_relationships?.length > 0 ? (
                    selectedContextSection.data.top_relationships.map((rel: any, idx: number) => {
                      // Use entity_type from backend, fallback to ID format detection
                      const entityId = rel.entity_id || rel.name;
                      const entityType = rel.entity_type || (/^[0-9A-Fa-f]{8}$/.test(entityId) ? 'qube' : 'human');
                      const isOwner = entityId === userId || rel.name === userId;

                      // Format the display name
                      let displayName = rel.name;
                      let entityLabel = '';
                      let entityIcon = '👤';

                      if (entityType === 'qube') {
                        // It's a Qube - show "Name (ID)" if name differs from ID
                        entityIcon = '🤖';
                        if (rel.name && rel.name !== entityId) {
                          displayName = `${rel.name} (${entityId})`;
                        } else {
                          displayName = entityId;
                        }
                      } else if (isOwner) {
                        // It's the owner
                        entityLabel = '(owner)';
                        entityIcon = '👑';
                      } else {
                        // It's another human
                        entityLabel = '(human)';
                      }

                      // Status icon override
                      if (rel.status === 'connected') entityIcon = '🤝';
                      else if (rel.status === 'friend') entityIcon = '💚';
                      else if (rel.status === 'close_friend') entityIcon = '💜';
                      else if (rel.status === 'best_friend') entityIcon = '💛';
                      else if (rel.status === 'blocked') entityIcon = '🚫';

                      return (
                        <div key={idx} className="p-3 bg-glass-bg/30 rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-text-primary font-medium flex items-center gap-2">
                              <span>{entityIcon}</span>
                              {displayName}
                              {entityLabel && (
                                <span className="text-xs text-text-tertiary">{entityLabel}</span>
                              )}
                            </span>
                            <span className="text-xs text-text-tertiary capitalize">{rel.status}</span>
                          </div>
                          <div className="flex gap-4 text-sm">
                            <span>
                              <span className="text-text-tertiary">Trust: </span>
                              {(() => {
                                // Handle trust_level - could be 0-1 (decimal) or 0-100 (percentage)
                                const rawTrust = rel.trust_level || 0;
                                const trustPercent = rawTrust > 1 ? Math.min(Math.round(rawTrust), 100) : Math.min(Math.round(rawTrust * 100), 100);
                                const trustColor = trustPercent >= 80 ? 'text-emerald-400' : trustPercent >= 60 ? 'text-accent-primary' : 'text-yellow-400';
                                return <span className={trustColor}>{trustPercent}%</span>;
                              })()}
                            </span>
                            <span>
                              <span className="text-text-tertiary">Interactions: </span>
                              <span className="text-text-secondary">{rel.interaction_count}</span>
                            </span>
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="text-text-tertiary p-4 bg-glass-bg/20 rounded-lg text-center">
                      <div className="text-4xl mb-2">👥</div>
                      <p>No relationships yet.</p>
                    </div>
                  )}
                </div>
              )}

              {/* Skills */}
              {selectedContextSection.type === 'skills' && (
                <div className="space-y-3">
                  <div className="flex gap-4 text-sm text-text-tertiary mb-4">
                    <span>Total XP: <span className="text-accent-primary">{selectedContextSection.data?.totals?.total_xp || 0}</span></span>
                    <span>Unlocked: <span className="text-accent-primary">{selectedContextSection.data?.totals?.unlocked_skills || 0}</span></span>
                    <span>Categories: <span className="text-accent-primary">{selectedContextSection.data?.totals?.categories || 0}</span></span>
                  </div>
                  {selectedContextSection.data?.categories && Object.keys(selectedContextSection.data.categories).length > 0 ? (
                    Object.values(selectedContextSection.data.categories).map((category: any) => (
                      <ExpandableSkillCategory key={category.category_id} category={category} />
                    ))
                  ) : (
                    <div className="text-text-tertiary p-4 bg-glass-bg/20 rounded-lg text-center">
                      <div className="text-4xl mb-2">⚡</div>
                      <p>No skills recorded yet.</p>
                    </div>
                  )}
                </div>
              )}

              {/* Wallet/Financial (type: 'financial' or legacy 'wallet') */}
              {(selectedContextSection.type === 'wallet' || selectedContextSection.type === 'financial') && selectedContextSection.data && (
                <div className="space-y-4">
                  <div className="p-3 bg-glass-bg/30 rounded-lg">
                    <span className="text-text-tertiary text-sm">P2SH Address:</span>
                    <div className="text-text-primary font-mono text-xs mt-1 break-all">
                      {selectedContextSection.data.p2sh_address}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 bg-glass-bg/30 rounded-lg">
                      <span className="text-text-tertiary text-sm">Balance:</span>
                      <div className="text-emerald-400 text-lg mt-1">
                        {(selectedContextSection.data.balance_sats || 0) / 100_000_000} BCH
                      </div>
                    </div>
                  </div>
                  {selectedContextSection.data.recent_transactions?.length > 0 && (
                    <div>
                      <span className="text-text-tertiary text-sm">Recent Transactions:</span>
                      <div className="mt-2 space-y-2">
                        {selectedContextSection.data.recent_transactions.map((tx: any, idx: number) => (
                          <div key={idx} className="flex items-center justify-between p-2 bg-glass-bg/20 rounded">
                            <span className={tx.type === 'received' ? 'text-emerald-400' : 'text-red-400'}>
                              {tx.type === 'received' ? '↓ Received' : '↑ Sent'}
                            </span>
                            <span className={tx.type === 'received' ? 'text-emerald-400' : 'text-red-400'}>
                              {tx.type === 'received' ? '+' : '-'}{Math.abs(tx.amount_sats) / 100_000_000} BCH
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Semantic Recalls (type: 'recalled' or legacy 'semantic_recalls') */}
              {(selectedContextSection.type === 'semantic_recalls' || selectedContextSection.type === 'recalled') && (
                <div className="space-y-2">
                  {selectedContextSection.data?.blocks?.length > 0 ? (
                    selectedContextSection.data.blocks.map((block: any, idx: number) => (
                      <div key={idx} className="p-3 bg-glass-bg/30 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className={`text-xs px-2 py-0.5 rounded ${
                              block.block_type === 'MESSAGE' ? 'bg-emerald-400/20 text-emerald-400' :
                              block.block_type === 'SUMMARY' ? 'bg-fuchsia-400/20 text-fuchsia-400' :
                              'bg-glass-bg/50 text-text-secondary'
                            }`}>
                              {block.block_type}
                            </span>
                            <span className="text-text-tertiary text-sm">#{block.block_number}</span>
                          </div>
                          {block.relevance_score !== undefined && (
                            <span className={`text-sm ${
                              block.relevance_score >= 0.8 ? 'text-emerald-400' :
                              block.relevance_score >= 0.6 ? 'text-accent-primary' :
                              'text-yellow-400'
                            }`}>
                              {Math.round(block.relevance_score * 100)}% match
                            </span>
                          )}
                        </div>
                        <p className="text-text-secondary text-sm">{block.preview}</p>
                      </div>
                    ))
                  ) : (
                    <div className="text-text-tertiary p-4 bg-glass-bg/20 rounded-lg text-center">
                      <div className="text-4xl mb-2">🔮</div>
                      <p>No relevant memories recalled.</p>
                    </div>
                  )}
                </div>
              )}

              {/* Recent Permanent / History (type: 'history' or legacy 'recent_permanent') */}
              {(selectedContextSection.type === 'recent_permanent' || selectedContextSection.type === 'history') && (
                <div className="space-y-2">
                  {selectedContextSection.data?.blocks?.length > 0 ? (
                    selectedContextSection.data.blocks.map((block: any, idx: number) => (
                      <div key={idx} className="p-3 bg-glass-bg/30 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className={`text-xs px-2 py-0.5 rounded ${
                              block.block_type === 'MESSAGE' ? 'bg-emerald-400/20 text-emerald-400' :
                              block.block_type === 'SUMMARY' ? 'bg-fuchsia-400/20 text-fuchsia-400' :
                              'bg-glass-bg/50 text-text-secondary'
                            }`}>
                              {block.block_type}
                            </span>
                            <span className="text-text-tertiary text-sm">#{block.block_number}</span>
                          </div>
                        </div>
                        <p className="text-text-secondary text-sm">{block.preview}</p>
                      </div>
                    ))
                  ) : (
                    <div className="text-text-tertiary p-4 bg-glass-bg/20 rounded-lg text-center">
                      <div className="text-4xl mb-2">📚</div>
                      <p>No recent permanent blocks.</p>
                    </div>
                  )}
                </div>
              )}

              {/* Session Blocks */}
              {selectedContextSection.type === 'session' && (
                <div className="space-y-2">
                  {selectedContextSection.data?.blocks?.blocks?.length > 0 ? (
                    selectedContextSection.data.blocks.blocks.map((block: any, idx: number) => (
                      <div key={idx} className="p-3 bg-glass-bg/30 rounded-lg border-l-2 border-dashed border-sky-400/50">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className={`text-xs px-2 py-0.5 rounded ${
                              block.block_type === 'MESSAGE' ? 'bg-emerald-400/20 text-emerald-400' :
                              block.block_type === 'SUMMARY' ? 'bg-fuchsia-400/20 text-fuchsia-400' :
                              'bg-glass-bg/50 text-text-secondary'
                            }`}>
                              {block.block_type}
                            </span>
                            <span className="text-text-tertiary text-sm">#{block.block_number}</span>
                          </div>
                        </div>
                        <p className="text-text-secondary text-sm">{block.preview}</p>
                      </div>
                    ))
                  ) : (
                    <div className="text-text-tertiary p-4 bg-glass-bg/20 rounded-lg text-center">
                      <div className="text-4xl mb-2">⚡</div>
                      <p>No session blocks yet.</p>
                    </div>
                  )}
                </div>
              )}

              {/* Stats */}
              {selectedContextSection.type === 'stats' && selectedContextSection.data && (
                <div className="space-y-4">
                  {/* Overview Grid */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="p-3 bg-glass-bg/30 rounded-lg">
                      <span className="text-text-tertiary text-xs">Total Tokens</span>
                      <div className="text-2xl font-display text-accent-primary mt-1">
                        {(selectedContextSection.data.total_tokens || 0).toLocaleString()}
                      </div>
                    </div>
                    <div className="p-3 bg-glass-bg/30 rounded-lg">
                      <span className="text-text-tertiary text-xs">Total Cost</span>
                      <div className="text-2xl font-display text-emerald-400 mt-1">
                        ${(selectedContextSection.data.total_cost || 0).toFixed(4)}
                      </div>
                    </div>
                    <div className="p-3 bg-glass-bg/30 rounded-lg">
                      <span className="text-text-tertiary text-xs">Total Anchors</span>
                      <div className="text-2xl font-display text-accent-primary mt-1">
                        {Number(selectedContextSection.data.total_anchors) || 0}
                      </div>
                    </div>
                  </div>

                  {/* Model Switches Breakdown */}
                  <div className="p-3 bg-glass-bg/20 rounded-lg">
                    <div className="text-text-tertiary text-xs uppercase tracking-wider mb-3">Model Switches</div>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-text-secondary">🔄 Revolver</span>
                        <span className="text-text-primary font-mono">{selectedContextSection.data.model_switches?.revolver || 0}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-text-secondary">🤖 Autonomous</span>
                        <span className="text-text-primary font-mono">{selectedContextSection.data.model_switches?.autonomous || 0}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-text-secondary">👆 Manual</span>
                        <span className="text-text-primary font-mono">{selectedContextSection.data.model_switches?.manual || 0}</span>
                      </div>
                      <div className="flex justify-between text-sm border-t border-glass-border pt-2 mt-2">
                        <span className="text-text-primary font-medium">📊 Total</span>
                        <span className="text-text-primary font-mono font-medium">
                          {(selectedContextSection.data.model_switches?.revolver || 0) +
                           (selectedContextSection.data.model_switches?.autonomous || 0) +
                           (selectedContextSection.data.model_switches?.manual || 0)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Tokens by Model */}
                  {selectedContextSection.data.tokens_by_model && Object.keys(selectedContextSection.data.tokens_by_model).length > 0 && (
                    <div className="p-3 bg-glass-bg/20 rounded-lg">
                      <div className="text-text-tertiary text-xs uppercase tracking-wider mb-3">Tokens by Model</div>
                      <div className="space-y-2">
                        {Object.entries(selectedContextSection.data.tokens_by_model).map(([model, tokens]: [string, any]) => (
                          <div key={model} className="flex justify-between text-sm">
                            <span className="text-text-secondary">{model}</span>
                            <span className="text-text-primary font-mono">{tokens.toLocaleString()}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* API Calls by Tool */}
                  {selectedContextSection.data.api_calls_by_tool && Object.keys(selectedContextSection.data.api_calls_by_tool).length > 0 && (
                    <div className="p-3 bg-glass-bg/20 rounded-lg">
                      <div className="text-text-tertiary text-xs uppercase tracking-wider mb-3">API Calls by Tool</div>
                      <div className="space-y-2">
                        {Object.entries(selectedContextSection.data.api_calls_by_tool).map(([tool, count]: [string, any]) => (
                          <div key={tool} className="flex justify-between text-sm">
                            <span className="text-text-secondary">{tool.replace(/_/g, ' ')}</span>
                            <span className="text-text-primary font-mono">{count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Block Counts - Only show active types with non-zero counts */}
                  {selectedContextSection.data.block_counts && (() => {
                    const ACTIVE_BLOCK_TYPES = ['GENESIS', 'MESSAGE', 'ACTION', 'SUMMARY', 'GAME'];
                    const filteredCounts = Object.entries(selectedContextSection.data.block_counts)
                      .filter(([type, count]: [string, any]) => ACTIVE_BLOCK_TYPES.includes(type) && count > 0);
                    return filteredCounts.length > 0 ? (
                      <div className="p-3 bg-glass-bg/20 rounded-lg">
                        <div className="text-text-tertiary text-xs uppercase tracking-wider mb-3">Block Counts</div>
                        <div className="flex flex-wrap gap-2">
                          {filteredCounts.map(([type, count]: [string, any]) => (
                            <span
                              key={type}
                              className={`text-xs px-2 py-1 rounded ${
                                type === 'MESSAGE' ? 'bg-emerald-400/20 text-emerald-400' :
                                type === 'SUMMARY' ? 'bg-fuchsia-400/20 text-fuchsia-400' :
                                type === 'ACTION' ? 'bg-amber-400/20 text-amber-400' :
                                type === 'GENESIS' ? 'bg-red-500/20 text-red-500' :
                                type === 'GAME' ? 'bg-yellow-400/20 text-yellow-400' :
                                'bg-glass-bg/50 text-text-secondary'
                              }`}
                            >
                              {type}: {count}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : null;
                  })()}

                  {/* First/Last Interaction */}
                  {(selectedContextSection.data.first_interaction || selectedContextSection.data.last_interaction) && (
                    <div className="p-3 bg-glass-bg/20 rounded-lg grid grid-cols-2 gap-3">
                      {selectedContextSection.data.first_interaction && (
                        <div>
                          <span className="text-text-tertiary text-xs">First Interaction</span>
                          <div className="text-text-primary text-sm mt-1">
                            {new Date(selectedContextSection.data.first_interaction * 1000).toLocaleDateString()}
                          </div>
                        </div>
                      )}
                      {selectedContextSection.data.last_interaction && (
                        <div>
                          <span className="text-text-tertiary text-xs">Last Interaction</span>
                          <div className="text-text-primary text-sm mt-1">
                            {new Date(selectedContextSection.data.last_interaction * 1000).toLocaleDateString()}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Settings */}
              {selectedContextSection.type === 'settings' && selectedContextSection.data && (
                <div className="space-y-4">
                  {/* Model Mode - Show only the active mode with color coding */}
                  {/* Colors: Manual=yellow, Revolver=green, Autonomous=purple */}
                  <div className={`p-4 rounded-lg text-center ${
                    selectedContextSection.data.model_mode === 'Revolver'
                      ? 'bg-emerald-500/20 border border-emerald-500/30'
                      : selectedContextSection.data.model_mode === 'Autonomous'
                      ? 'bg-purple-500/20 border border-purple-500/30'
                      : 'bg-yellow-500/20 border border-yellow-500/30'
                  }`}>
                    <div className="text-3xl mb-2">
                      {selectedContextSection.data.model_mode === 'Revolver' ? '🎰' :
                       selectedContextSection.data.model_mode === 'Autonomous' ? '🤖' : '🔒'}
                    </div>
                    <h3 className={`text-xl font-display ${
                      selectedContextSection.data.model_mode === 'Revolver'
                        ? 'text-emerald-400'
                        : selectedContextSection.data.model_mode === 'Autonomous'
                        ? 'text-purple-400'
                        : 'text-yellow-400'
                    }`}>
                      {selectedContextSection.data.model_mode === 'Revolver' ? 'Revolver Mode' :
                       selectedContextSection.data.model_mode === 'Autonomous' ? 'Autonomous' : 'Manual Mode'}
                    </h3>
                    {selectedContextSection.data.model_locked_to && selectedContextSection.data.model_mode === 'Manual' && (
                      <div className="text-text-secondary text-sm mt-1">
                        Locked to: {formatModelName(selectedContextSection.data.model_locked_to)}
                      </div>
                    )}
                  </div>

                  {/* Model Pool - show for Revolver or Autonomous mode */}
                  {selectedContextSection.data.model_mode === 'Revolver' && (selectedContextSection.data.revolver_mode_pool?.length === 0 ? (
                    <div className="p-3 bg-glass-bg/20 rounded-lg">
                      <div className="text-text-tertiary text-xs uppercase tracking-wider mb-2">Model Pool</div>
                      <div className="text-text-secondary text-sm italic">All available models (no restrictions)</div>
                    </div>
                  ) : (() => {
                    // Provider colors and labels
                    const PROVIDER_CONFIG: Record<string, { label: string; bg: string; text: string; border: string }> = {
                      openai: { label: 'OpenAI', bg: 'bg-rose-500/10', text: 'text-rose-400', border: 'border-rose-500/30' },
                      anthropic: { label: 'Anthropic', bg: 'bg-orange-500/10', text: 'text-orange-400', border: 'border-orange-500/30' },
                      google: { label: 'Google', bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30' },
                      venice: { label: 'Venice', bg: 'bg-violet-500/10', text: 'text-violet-400', border: 'border-violet-500/30' },
                      deepseek: { label: 'DeepSeek', bg: 'bg-cyan-500/10', text: 'text-cyan-400', border: 'border-cyan-500/30' },
                      xai: { label: 'xAI', bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30' },
                      perplexity: { label: 'Perplexity', bg: 'bg-lime-500/10', text: 'text-lime-400', border: 'border-lime-500/30' },
                      openrouter: { label: 'OpenRouter', bg: 'bg-fuchsia-500/10', text: 'text-fuchsia-400', border: 'border-fuchsia-500/30' },
                      ollama: { label: 'Ollama', bg: 'bg-slate-500/10', text: 'text-slate-400', border: 'border-slate-500/30' },
                      nanogpt: { label: 'NanoGPT', bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/30' },
                      other: { label: 'Other', bg: 'bg-gray-500/10', text: 'text-gray-400', border: 'border-gray-500/30' },
                    };
                    const KNOWN_PROVIDERS = Object.keys(PROVIDER_CONFIG).filter(p => p !== 'other');

                    // Group models by provider
                    const grouped: Record<string, string[]> = {};
                    selectedContextSection.data.revolver_mode_pool
                      .filter((model: string) => model && model.trim() && !/^\d+b$/i.test(model.trim()))
                      .forEach((model: string) => {
                        const colonIdx = model.indexOf(':');
                        let provider = 'other';
                        let modelId = model;
                        if (colonIdx > 0) {
                          const possibleProvider = model.substring(0, colonIdx).toLowerCase();
                          if (KNOWN_PROVIDERS.includes(possibleProvider)) {
                            provider = possibleProvider;
                            modelId = model.substring(colonIdx + 1);
                          }
                        }
                        if (!grouped[provider]) grouped[provider] = [];
                        grouped[provider].push(modelId);
                      });

                    // Sort providers: known first (in order), then 'other'
                    const sortedProviders = [...KNOWN_PROVIDERS.filter(p => grouped[p]), ...(grouped['other'] ? ['other'] : [])];

                    return (
                      <div className="p-3 bg-glass-bg/20 rounded-lg">
                        <div className="text-text-tertiary text-xs uppercase tracking-wider mb-3">Model Pool</div>
                        <div className="space-y-2">
                          {sortedProviders.map(provider => {
                            const config = PROVIDER_CONFIG[provider];
                            const models = grouped[provider] || [];
                            return (
                              <div key={provider} className={`p-2 rounded-lg border ${config.bg} ${config.border}`}>
                                <div className={`text-xs font-medium mb-1.5 ${config.text}`}>{config.label}</div>
                                <div className="flex flex-wrap gap-1">
                                  {models.map((modelId, idx) => (
                                    <span key={idx} className={`text-xs px-1.5 py-0.5 rounded ${config.bg} ${config.text} border ${config.border}`}>
                                      {formatModelName(modelId)}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })())}

                  {selectedContextSection.data.model_mode === 'Autonomous' && (selectedContextSection.data.autonomous_mode_pool?.length === 0 ? (
                    <div className="p-3 bg-glass-bg/20 rounded-lg">
                      <div className="text-text-tertiary text-xs uppercase tracking-wider mb-2">Model Pool</div>
                      <div className="text-text-secondary text-sm italic">All available models (Qube decides)</div>
                    </div>
                  ) : (() => {
                    // Provider colors and labels
                    const PROVIDER_CONFIG: Record<string, { label: string; bg: string; text: string; border: string }> = {
                      openai: { label: 'OpenAI', bg: 'bg-rose-500/10', text: 'text-rose-400', border: 'border-rose-500/30' },
                      anthropic: { label: 'Anthropic', bg: 'bg-orange-500/10', text: 'text-orange-400', border: 'border-orange-500/30' },
                      google: { label: 'Google', bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30' },
                      venice: { label: 'Venice', bg: 'bg-violet-500/10', text: 'text-violet-400', border: 'border-violet-500/30' },
                      deepseek: { label: 'DeepSeek', bg: 'bg-cyan-500/10', text: 'text-cyan-400', border: 'border-cyan-500/30' },
                      xai: { label: 'xAI', bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30' },
                      perplexity: { label: 'Perplexity', bg: 'bg-lime-500/10', text: 'text-lime-400', border: 'border-lime-500/30' },
                      openrouter: { label: 'OpenRouter', bg: 'bg-fuchsia-500/10', text: 'text-fuchsia-400', border: 'border-fuchsia-500/30' },
                      ollama: { label: 'Ollama', bg: 'bg-slate-500/10', text: 'text-slate-400', border: 'border-slate-500/30' },
                      nanogpt: { label: 'NanoGPT', bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/30' },
                      other: { label: 'Other', bg: 'bg-gray-500/10', text: 'text-gray-400', border: 'border-gray-500/30' },
                    };
                    const KNOWN_PROVIDERS = Object.keys(PROVIDER_CONFIG).filter(p => p !== 'other');

                    // Group models by provider
                    const grouped: Record<string, string[]> = {};
                    selectedContextSection.data.autonomous_mode_pool
                      .filter((model: string) => model && model.trim() && !/^\d+b$/i.test(model.trim()))
                      .forEach((model: string) => {
                        const colonIdx = model.indexOf(':');
                        let provider = 'other';
                        let modelId = model;
                        if (colonIdx > 0) {
                          const possibleProvider = model.substring(0, colonIdx).toLowerCase();
                          if (KNOWN_PROVIDERS.includes(possibleProvider)) {
                            provider = possibleProvider;
                            modelId = model.substring(colonIdx + 1);
                          }
                        }
                        if (!grouped[provider]) grouped[provider] = [];
                        grouped[provider].push(modelId);
                      });

                    // Sort providers: known first (in order), then 'other'
                    const sortedProviders = [...KNOWN_PROVIDERS.filter(p => grouped[p]), ...(grouped['other'] ? ['other'] : [])];

                    return (
                      <div className="p-3 bg-glass-bg/20 rounded-lg">
                        <div className="text-text-tertiary text-xs uppercase tracking-wider mb-3">Model Pool</div>
                        <div className="space-y-2">
                          {sortedProviders.map(provider => {
                            const config = PROVIDER_CONFIG[provider];
                            const models = grouped[provider] || [];
                            return (
                              <div key={provider} className={`p-2 rounded-lg border ${config.bg} ${config.border}`}>
                                <div className={`text-xs font-medium mb-1.5 ${config.text}`}>{config.label}</div>
                                <div className="flex flex-wrap gap-1">
                                  {models.map((modelId, idx) => (
                                    <span key={idx} className={`text-xs px-1.5 py-0.5 rounded ${config.bg} ${config.text} border ${config.border}`}>
                                      {formatModelName(modelId)}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })())}

                  {/* Memory & Anchoring */}
                  <div className="p-3 bg-glass-bg/20 rounded-lg">
                    <div className="text-text-tertiary text-xs uppercase tracking-wider mb-3">Memory & Anchoring</div>
                    <div className="space-y-3">
                      {/* Individual Chat */}
                      <div className="space-y-1">
                        <div className="text-text-tertiary text-xs">Individual Chat</div>
                        <div className="flex justify-between items-center">
                          <span className="text-text-secondary">Auto-Anchor</span>
                          <span className={`text-xs px-2 py-1 rounded ${
                            selectedContextSection.data.individual_auto_anchor_enabled ? 'bg-accent-primary/20 text-accent-primary' : 'bg-glass-bg/50 text-text-tertiary'
                          }`}>
                            {selectedContextSection.data.individual_auto_anchor_enabled ? 'Enabled' : 'Disabled'}
                          </span>
                        </div>
                        {selectedContextSection.data.individual_auto_anchor_enabled && (
                          <div className="flex justify-between items-center">
                            <span className="text-text-secondary">Threshold</span>
                            <span className="text-text-primary text-sm">{selectedContextSection.data.individual_auto_anchor_threshold} messages</span>
                          </div>
                        )}
                      </div>
                      {/* Group Chat */}
                      <div className="space-y-1">
                        <div className="text-text-tertiary text-xs">Group Chat</div>
                        <div className="flex justify-between items-center">
                          <span className="text-text-secondary">Auto-Anchor</span>
                          <span className={`text-xs px-2 py-1 rounded ${
                            selectedContextSection.data.group_auto_anchor_enabled ? 'bg-accent-primary/20 text-accent-primary' : 'bg-glass-bg/50 text-text-tertiary'
                          }`}>
                            {selectedContextSection.data.group_auto_anchor_enabled ? 'Enabled' : 'Disabled'}
                          </span>
                        </div>
                        {selectedContextSection.data.group_auto_anchor_enabled && (
                          <div className="flex justify-between items-center">
                            <span className="text-text-secondary">Threshold</span>
                            <span className="text-text-primary text-sm">{selectedContextSection.data.group_auto_anchor_threshold} messages</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Voice & Interface */}
                  <div className="p-3 bg-glass-bg/20 rounded-lg">
                    <div className="text-text-tertiary text-xs uppercase tracking-wider mb-3">Voice & Interface</div>
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-text-secondary">TTS</span>
                        <span className={`text-xs px-2 py-1 rounded ${
                          selectedContextSection.data.tts_enabled ? 'bg-accent-primary/20 text-accent-primary' : 'bg-glass-bg/50 text-text-tertiary'
                        }`}>
                          {selectedContextSection.data.tts_enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </div>
                      {selectedContextSection.data.voice_model && (
                        <div className="flex justify-between items-center">
                          <span className="text-text-secondary">Voice Model</span>
                          <span className="text-text-primary text-sm">{formatVoiceName(selectedContextSection.data.voice_model)}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Visualizer */}
                  <div className="p-3 bg-glass-bg/20 rounded-lg">
                    <div className="flex items-center justify-between mb-3">
                      <div className="text-text-tertiary text-xs uppercase tracking-wider">Visualizer</div>
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        selectedContextSection.data.visualizer?.enabled ? 'bg-cyan-500/20 text-cyan-400' : 'bg-glass-bg/50 text-text-tertiary'
                      }`}>
                        {selectedContextSection.data.visualizer?.enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>
                    {selectedContextSection.data.visualizer?.enabled && (
                      <div className="space-y-2">
                        <div className="flex justify-between items-center">
                          <span className="text-text-secondary">Waveform Style</span>
                          <span className="text-text-primary text-sm">
                            {['Classic Bars', 'Symmetric Bars', 'Smooth Waveform', 'Radial Spectrum', 'Dot Matrix', 'Polygon Morph', 'Concentric Circles', 'Spiral Wave', 'Particle Field', 'Ring Bars', 'Wave Mesh'][selectedContextSection.data.visualizer.waveform_style - 1] || `Style ${selectedContextSection.data.visualizer.waveform_style}`}
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-text-secondary">Color Theme</span>
                          <span className="text-text-primary text-sm capitalize">
                            {selectedContextSection.data.visualizer.color_theme?.replace(/-/g, ' ') || 'Qube Color'}
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-text-secondary">Sensitivity</span>
                          <div className="flex items-center gap-2">
                            <div className="w-12 h-1.5 bg-glass-bg/50 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-cyan-400 transition-all"
                                style={{ width: `${selectedContextSection.data.visualizer.sensitivity || 50}%` }}
                              />
                            </div>
                            <span className="text-text-tertiary text-xs">{selectedContextSection.data.visualizer.sensitivity || 50}%</span>
                          </div>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-text-secondary">Smoothness</span>
                          <span className="text-text-primary text-sm capitalize">
                            {selectedContextSection.data.visualizer.animation_smoothness || 'Medium'}
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-text-secondary">Frequency Range</span>
                          <span className="text-text-primary text-sm">{selectedContextSection.data.visualizer.frequency_range || 20}%</span>
                        </div>
                        {selectedContextSection.data.visualizer.audio_offset_ms !== 0 && (
                          <div className="flex justify-between items-center">
                            <span className="text-text-secondary">Audio Offset</span>
                            <span className="text-text-primary text-sm">{selectedContextSection.data.visualizer.audio_offset_ms}ms</span>
                          </div>
                        )}
                        <div className="flex justify-between items-center">
                          <span className="text-text-secondary">Output Monitor</span>
                          <span className="text-text-primary text-sm">
                            {selectedContextSection.data.visualizer.output_monitor === 0 ? 'Primary' : `Monitor ${selectedContextSection.data.visualizer.output_monitor}`}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Mood */}
              {selectedContextSection.type === 'mood' && selectedContextSection.data && (
                <div className="space-y-4">
                  <div className="text-center p-6 bg-glass-bg/30 rounded-lg">
                    <div className="text-6xl mb-3">
                      {(() => {
                        const moodEmojis: Record<string, string> = {
                          happy: '😊', excited: '🤩', neutral: '😐', curious: '🤔',
                          tired: '😴', stressed: '😰', sad: '😢', angry: '😠'
                        };
                        return moodEmojis[selectedContextSection.data.current_mood] || '😐';
                      })()}
                    </div>
                    <h3 className="text-xl font-display text-text-primary capitalize">
                      {selectedContextSection.data.current_mood || 'Neutral'}
                    </h3>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 bg-glass-bg/20 rounded-lg">
                      <span className="text-text-tertiary text-xs">Energy Level</span>
                      <div className="mt-2">
                        <div className="h-2 bg-glass-bg/50 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-yellow-400 transition-all"
                            style={{ width: `${(selectedContextSection.data.energy_level || 0) * 10}%` }}
                          />
                        </div>
                        <div className="text-right text-xs text-text-tertiary mt-1">
                          {selectedContextSection.data.energy_level || 0}/10
                        </div>
                      </div>
                    </div>
                    <div className="p-3 bg-glass-bg/20 rounded-lg">
                      <span className="text-text-tertiary text-xs">Stress Level</span>
                      <div className="mt-2">
                        <div className="h-2 bg-glass-bg/50 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-red-400 transition-all"
                            style={{ width: `${(selectedContextSection.data.stress_level || 0) * 10}%` }}
                          />
                        </div>
                        <div className="text-right text-xs text-text-tertiary mt-1">
                          {selectedContextSection.data.stress_level || 0}/10
                        </div>
                      </div>
                    </div>
                  </div>

                  {selectedContextSection.data.last_update && (
                    <div className="text-text-tertiary text-xs text-center">
                      Last updated: {new Date(selectedContextSection.data.last_update * 1000).toLocaleString()}
                    </div>
                  )}
                </div>
              )}

              {/* Health */}
              {selectedContextSection.type === 'health' && selectedContextSection.data && (
                <div className="space-y-4">
                  <div className={`p-4 rounded-lg text-center ${
                    selectedContextSection.data.overall_status === 'healthy'
                      ? 'bg-emerald-500/20 border border-emerald-500/30'
                      : 'bg-yellow-500/20 border border-yellow-500/30'
                  }`}>
                    <div className="text-4xl mb-2">
                      {selectedContextSection.data.overall_status === 'healthy' ? '💚' : '⚠️'}
                    </div>
                    <h3 className={`text-xl font-display capitalize ${
                      selectedContextSection.data.overall_status === 'healthy'
                        ? 'text-emerald-400'
                        : 'text-yellow-400'
                    }`}>
                      {selectedContextSection.data.overall_status || 'Unknown'}
                    </h3>
                  </div>

                  <div className="p-3 bg-glass-bg/20 rounded-lg">
                    <div className="flex justify-between items-center">
                      <span className="text-text-secondary">Integrity Verified</span>
                      <span className={`text-xs px-2 py-1 rounded ${
                        selectedContextSection.data.integrity_verified
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : 'bg-red-500/20 text-red-400'
                      }`}>
                        {selectedContextSection.data.integrity_verified ? 'Verified' : 'Not Verified'}
                      </span>
                    </div>
                  </div>

                  {selectedContextSection.data.issues && selectedContextSection.data.issues.length > 0 && (
                    <div className="p-3 bg-red-500/10 rounded-lg border border-red-500/30">
                      <div className="text-red-400 text-xs uppercase tracking-wider mb-2">Issues</div>
                      <ul className="space-y-1">
                        {selectedContextSection.data.issues.map((issue: string, idx: number) => (
                          <li key={idx} className="text-text-secondary text-sm flex items-start gap-2">
                            <span className="text-red-400">•</span>
                            {issue}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {selectedContextSection.data.last_check && (
                    <div className="text-text-tertiary text-xs text-center">
                      Last checked: {new Date(selectedContextSection.data.last_check * 1000).toLocaleString()}
                    </div>
                  )}
                </div>
              )}

              {/* Chain */}
              {selectedContextSection.type === 'chain' && selectedContextSection.data && (
                <div className="space-y-4">
                  {/* Block Counts */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="p-3 bg-glass-bg/30 rounded-lg text-center">
                      <span className="text-text-tertiary text-xs">Total</span>
                      <div className="text-2xl font-display text-accent-primary mt-1">
                        {selectedContextSection.data.total_blocks || 0}
                      </div>
                    </div>
                    <div className="p-3 bg-glass-bg/30 rounded-lg text-center">
                      <span className="text-text-tertiary text-xs">Permanent</span>
                      <div className="text-2xl font-display text-fuchsia-400 mt-1">
                        {selectedContextSection.data.permanent_blocks || 0}
                      </div>
                    </div>
                    <div className="p-3 bg-glass-bg/30 rounded-lg text-center">
                      <span className="text-text-tertiary text-xs">Session</span>
                      <div className="text-2xl font-display text-sky-400 mt-1">
                        {selectedContextSection.data.session_blocks || 0}
                      </div>
                    </div>
                  </div>

                  {/* Hashes */}
                  {selectedContextSection.data.genesis_hash && (
                    <div className="p-3 bg-glass-bg/20 rounded-lg">
                      <span className="text-text-tertiary text-xs">Genesis Hash</span>
                      <div className="text-text-primary font-mono text-xs mt-1 break-all">
                        {selectedContextSection.data.genesis_hash}
                      </div>
                    </div>
                  )}
                  {selectedContextSection.data.latest_block_hash && (
                    <div className="p-3 bg-glass-bg/20 rounded-lg">
                      <span className="text-text-tertiary text-xs">Latest Block Hash</span>
                      <div className="text-text-primary font-mono text-xs mt-1 break-all">
                        {selectedContextSection.data.latest_block_hash}
                      </div>
                    </div>
                  )}

                  {/* Last Anchor */}
                  {selectedContextSection.data.last_anchor_block && (
                    <div className="p-3 bg-glass-bg/20 rounded-lg">
                      <div className="flex justify-between items-center">
                        <span className="text-text-secondary">Last Anchor Block</span>
                        <span className="text-accent-primary font-mono">#{selectedContextSection.data.last_anchor_block}</span>
                      </div>
                    </div>
                  )}

                  {/* Block Type Breakdown - Only show active types with non-zero counts */}
                  {selectedContextSection.data.block_counts && (() => {
                    const ACTIVE_BLOCK_TYPES = ['GENESIS', 'MESSAGE', 'ACTION', 'SUMMARY', 'GAME'];
                    const filteredCounts = Object.entries(selectedContextSection.data.block_counts)
                      .filter(([type, count]: [string, any]) => ACTIVE_BLOCK_TYPES.includes(type) && count > 0);
                    return filteredCounts.length > 0 ? (
                      <div className="p-3 bg-glass-bg/20 rounded-lg">
                        <div className="text-text-tertiary text-xs uppercase tracking-wider mb-3">Block Types</div>
                        <div className="flex flex-wrap gap-2">
                          {filteredCounts.map(([type, count]: [string, any]) => (
                            <span
                              key={type}
                              className={`text-xs px-2 py-1 rounded ${
                                type === 'MESSAGE' ? 'bg-emerald-400/20 text-emerald-400' :
                                type === 'SUMMARY' ? 'bg-fuchsia-400/20 text-fuchsia-400' :
                                type === 'ACTION' ? 'bg-amber-400/20 text-amber-400' :
                                type === 'GENESIS' ? 'bg-red-500/20 text-red-500' :
                                type === 'GAME' ? 'bg-yellow-400/20 text-yellow-400' :
                                'bg-glass-bg/50 text-text-secondary'
                              }`}
                            >
                              {type}: {count}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : null;
                  })()}
                </div>
              )}
            </GlassCard>
          </div>
        ) : !selectedBlock ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="text-6xl mb-4">📄</div>
              <h2 className="text-xl font-display text-text-primary mb-2">
                No Block Selected
              </h2>
              <p className="text-text-secondary">
                Click on a block or context section to view details
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

                      {/* Trait Changes */}
                      {evaluation.trait_changes && evaluation.trait_changes[entityId] && (
                        (() => {
                          const changes = evaluation.trait_changes[entityId];
                          const hasChanges = changes.assigned?.length || changes.strengthened?.length ||
                                            changes.weakened?.length || changes.removed?.length;
                          if (!hasChanges) return null;

                          return (
                            <div className="mt-3 pt-3 border-t border-glass-border/30">
                              <h5 className="text-xs text-text-secondary font-semibold mb-2 flex items-center gap-1">
                                🧬 Trait Changes
                              </h5>
                              <div className="flex flex-wrap gap-1">
                                {changes.assigned?.map((trait: string) => (
                                  <span key={trait} className="px-2 py-0.5 text-xs bg-green-500/20 text-green-400 rounded-full border border-green-500/30">
                                    +{trait} <span className="text-[10px]">(NEW)</span>
                                  </span>
                                ))}
                                {changes.strengthened?.map((trait: string) => (
                                  <span key={trait} className="px-2 py-0.5 text-xs bg-blue-500/20 text-blue-400 rounded-full border border-blue-500/30">
                                    ↑{trait}
                                  </span>
                                ))}
                                {changes.weakened?.map((trait: string) => (
                                  <span key={trait} className="px-2 py-0.5 text-xs bg-orange-500/20 text-orange-400 rounded-full border border-orange-500/30">
                                    ↓{trait}
                                  </span>
                                ))}
                                {changes.removed?.map((trait: string) => (
                                  <span key={trait} className="px-2 py-0.5 text-xs bg-red-500/20 text-red-400 rounded-full border border-red-500/30 line-through">
                                    {trait}
                                  </span>
                                ))}
                              </div>
                            </div>
                          );
                        })()
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

            {/* Show multi-selected blocks info */}
            {selectedSessionBlocks.size > 0 ? (
              <div className="mb-4 p-3 bg-accent-warning/10 border border-accent-warning/30 rounded-lg">
                <div className="text-sm text-text-secondary mb-1">Selected Blocks:</div>
                <div className="text-sm font-mono text-accent-warning">
                  {selectedSessionBlocks.size} block{selectedSessionBlocks.size !== 1 ? 's' : ''} selected
                </div>
                <div className="text-xs text-text-tertiary mt-1">
                  {[...selectedSessionBlocks].sort((a, b) => b - a).slice(0, 5).map(n => `#${n}`).join(', ')}
                  {selectedSessionBlocks.size > 5 && ` +${selectedSessionBlocks.size - 5} more`}
                </div>
              </div>
            ) : selectedBlock && selectedBlock.block_number < 0 ? (
              <div className="mb-4 p-3 bg-accent-warning/10 border border-accent-warning/30 rounded-lg">
                <div className="text-sm text-text-secondary mb-1">Selected Block:</div>
                <div className="text-sm font-mono text-accent-warning">
                  Block #{selectedBlock.block_number} ({selectedBlock.block_type})
                </div>
              </div>
            ) : null}

            <p className="text-text-primary mb-6">
              {selectedSessionBlocks.size > 0 ? (
                <>You can discard the {selectedSessionBlocks.size} selected block{selectedSessionBlocks.size !== 1 ? 's' : ''} or all {sessionBlocks.length} session blocks. This action cannot be undone.</>
              ) : selectedBlock && selectedBlock.block_number < 0 ? (
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

              {/* Show "Discard Selected" if blocks are selected (multi or single) */}
              {(selectedSessionBlocks.size > 0 || (selectedBlock && selectedBlock.block_number < 0)) && (
                <GlassButton
                  variant="danger"
                  onClick={confirmDiscardSelected}
                  className="bg-accent-warning/20 hover:bg-accent-warning/30 text-accent-warning"
                >
                  Discard {selectedSessionBlocks.size > 0 ? selectedSessionBlocks.size : ''} Selected
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

      {/* Anchor Confirmation Modal */}
      {showAnchorConfirm && selectedQube && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50">
          <GlassCard className="p-6 max-w-md mx-4">
            <h2 className="text-xl font-display text-accent-primary mb-4">
              ⚓ Anchor Session to Chain?
            </h2>

            <div className="mb-4 p-3 bg-accent-primary/10 border border-accent-primary/30 rounded-lg">
              <div className="text-sm text-text-secondary mb-1">Session Blocks to Anchor:</div>
              <div className="text-lg font-mono text-accent-primary">
                {sessionBlocks.length} block{sessionBlocks.length !== 1 ? 's' : ''}
              </div>
            </div>

            <p className="text-text-primary mb-6">
              This will permanently commit {sessionBlocks.length} session block{sessionBlocks.length !== 1 ? 's' : ''} to <span className="font-semibold text-accent-primary">{selectedQube.name}</span>'s memory chain. These memories will become part of their permanent identity and cannot be undone.
            </p>

            <div className="flex gap-3 justify-end">
              <GlassButton
                variant="secondary"
                onClick={cancelAnchor}
              >
                Cancel
              </GlassButton>

              <GlassButton
                variant="primary"
                onClick={confirmAnchor}
              >
                ⚓ Anchor to Chain
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
