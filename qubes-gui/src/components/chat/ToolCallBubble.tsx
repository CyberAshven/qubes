import React, { useState } from 'react';

// Simple inline icons (no external library needed)
const ChevronDownIcon = ({ size = 14, className = '' }: { size?: number; className?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M6 9l6 6 6-6" />
  </svg>
);

const ChevronUpIcon = ({ size = 14, className = '' }: { size?: number; className?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M18 15l-6-6-6 6" />
  </svg>
);

const WrenchIcon = ({ size = 14, color = 'currentColor' }: { size?: number; color?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
  </svg>
);

const AlertIcon = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="text-red-400">
    <circle cx="12" cy="12" r="10" />
    <line x1="12" y1="8" x2="12" y2="12" />
    <line x1="12" y1="16" x2="12.01" y2="16" />
  </svg>
);

const LoaderIcon = ({ size = 14, color = 'currentColor' }: { size?: number; color?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="animate-spin">
    <path d="M21 12a9 9 0 1 1-6.219-8.56" />
  </svg>
);

interface ToolCallBubbleProps {
  toolName: string;
  input: any;
  result: any;
  status: 'in_progress' | 'completed' | 'failed';
  accentColor: string;
  timestamp?: number;
}

// Friendly display names for tools
const TOOL_DISPLAY_NAMES: Record<string, string> = {
  // Regular tools
  'web_search': 'Web Search',
  'generate_image': 'Image Generation',
  'browse_url': 'Browse URL',
  'memory_search': 'Memory Search',
  'list_files': 'List Files',
  'read_file': 'Read File',
  'write_file': 'Write File',
  'run_command': 'Run Command',
  'calculate': 'Calculate',
  // System tools
  'get_system_state': 'Get System State',
  'update_system_state': 'Update System State',
  'switch_model': 'Switch Model',
  'describe_my_avatar': 'Look in Mirror',
  // AI Reasoning Tools
  'think_step_by_step': 'Step-by-Step Thinking',
  'self_critique': 'Self Critique',
  'explore_alternatives': 'Explore Alternatives',
  // Social Intelligence Tools (Social & Emotional Learning)
  'get_relationship_context': 'Relationship Context',
  'recall_relationship_history': 'Recall History',
  'analyze_interaction_patterns': 'Analyze Patterns',
  'get_relationship_timeline': 'Get Timeline',
  'read_emotional_state': 'Read Emotions',
  'track_emotional_patterns': 'Track Emotions',
  'detect_mood_shift': 'Detect Mood',
  'adapt_communication_style': 'Adapt Style',
  'match_communication_style': 'Match Style',
  'calibrate_tone': 'Calibrate Tone',
  'steelman': 'Steelman',
  'devils_advocate': "Devil's Advocate",
  'spot_fallacy': 'Spot Fallacy',
  'assess_trust_level': 'Assess Trust',
  'detect_social_manipulation': 'Detect Manipulation',
  'evaluate_request': 'Evaluate Request',
  // Coding Tools (Phase 3) - Ship It theme
  'develop_code': 'Develop Code',
  'run_tests': 'Run Tests',
  'write_unit_test': 'Write Unit Test',
  'measure_coverage': 'Measure Coverage',
  'debug_code': 'Debug Code',
  'analyze_error': 'Analyze Error',
  'find_root_cause': 'Find Root Cause',
  'benchmark_code': 'Benchmark Code',
  'analyze_complexity': 'Analyze Complexity',
  'tune_performance': 'Tune Performance',
  'security_scan': 'Security Scan',
  'find_exploit': 'Find Exploit',
  'reverse_engineer': 'Reverse Engineer',
  'pen_test': 'Pen Test',
  'review_code': 'Review Code',
  'refactor_code': 'Refactor Code',
  'git_operation': 'Git Operation',
  'generate_docs': 'Generate Docs',
  // Creative Expression Tools (Phase 4) - Sovereignty Theme
  'refine_composition': 'Refine Composition',
  'apply_color_theory': 'Apply Color Theory',
  'compose_text': 'Compose Text',
  'craft_prose': 'Craft Prose',
  'write_poetry': 'Write Poetry',
  'compose_music': 'Compose Music',
  'create_melody': 'Create Melody',
  'design_harmony': 'Design Harmony',
  'craft_narrative': 'Craft Narrative',
  'develop_plot': 'Develop Plot',
  'design_character': 'Design Character',
  'build_world': 'Build World',
  'change_favorite_color': 'Change Color',
  'change_voice': 'Change Voice',
  'define_personality': 'Define Personality',
  'set_aspirations': 'Set Aspirations',
  // Memory & Recall Tools (Phase 5)
  'store_knowledge': 'Store Knowledge',
  'recall': 'Recall',
  'store_fact': 'Store Fact',
  'tag_memory': 'Tag Memory',
  'synthesize_knowledge': 'Synthesize Knowledge',
  'create_summary': 'Create Summary',
  'keyword_search': 'Keyword Search',
  'semantic_search': 'Semantic Search',
  'record_skill': 'Record Skill',
  'add_tags': 'Add Tags',
  'link_memories': 'Link Memories',
  'find_patterns': 'Find Patterns',
  'generate_insight': 'Generate Insight',
  'write_summary': 'Write Summary',
  'export_knowledge': 'Export Knowledge',
  // Security & Privacy Tools (Phase 6)
  'verify_chain_integrity': 'Verify Chain',
  'audit_chain': 'Audit Chain',
  'assess_sensitivity': 'Assess Sensitivity',
  'vet_qube': 'Vet Qube',
  'detect_threat': 'Detect Threat',
  'defend_reasoning': 'Defend Reasoning',
  'detect_tampering': 'Detect Tampering',
  'verify_anchor': 'Verify Anchor',
  'classify_data': 'Classify Data',
  'control_sharing': 'Control Sharing',
  'check_reputation': 'Check Reputation',
  'secure_group_chat': 'Group Security',
  'detect_technical_manipulation': 'Detect Manipulation',
  'detect_hostile_qube': 'Detect Hostile',
  'detect_injection': 'Detect Injection',
  'validate_reasoning': 'Validate Reasoning',
  // Board Games Tools (Phase 7)
  'play_game': 'Play Game',
  'chess_move': 'Chess Move',
  'analyze_game_state': 'Analyze Game',
  'plan_strategy': 'Plan Strategy',
  'learn_from_game': 'Learn from Game',
  'property_tycoon_action': 'Property Tycoon',
  'race_home_action': 'Race Home',
  'mystery_mansion_action': 'Mystery Mansion',
  'life_journey_action': 'Life Journey',
  // Finance Tools (Phase 8)
  'send_bch': 'Send BCH',
  'validate_transaction': 'Validate Transaction',
  'check_wallet_health': 'Wallet Health',
  'get_market_data': 'Market Data',
  'plan_savings': 'Plan Savings',
  'identify_token': 'Identify Token',
  'optimize_fees': 'Optimize Fees',
  'track_transaction': 'Track Transaction',
  'monitor_balance': 'Monitor Balance',
  'multisig_action': 'Multi-sig Action',
  'set_price_alert': 'Price Alert',
  'analyze_market_trend': 'Market Trend',
  'setup_dca': 'Setup DCA',
  'manage_cashtokens': 'Manage Tokens',
  // Special
  'revolver_switch': 'Revolver Switch',
};

// Truncate text to a max length
function truncateText(text: string, maxLength: number = 80): string {
  if (!text) return '';
  const str = typeof text === 'string' ? text : JSON.stringify(text);
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength) + '...';
}

// Format input for display - human readable
function formatInput(input: any, toolName?: string): string {
  if (!input) return '';
  if (typeof input === 'string') return input;

  // For objects, try to make them human-readable
  if (typeof input === 'object') {
    // Check if it's an empty object
    if (Object.keys(input).length === 0) {
      return '';
    }

    // Special handling for specific tools
    if (toolName === 'get_system_state' && input.sections) {
      const sections = Array.isArray(input.sections) ? input.sections : [input.sections];
      return sections.join(', ');
    }

    if (toolName === 'update_system_state') {
      const parts = [];
      if (input.path) parts.push(input.path);
      if (input.value !== undefined) {
        const val = typeof input.value === 'string' ? input.value : JSON.stringify(input.value);
        parts.push(`= ${val}`);
      }
      return parts.join(' ');
    }

    // Common input field names - try to extract the most relevant one
    const relevantFields = ['query', 'url', 'path', 'prompt', 'message', 'text', 'content', 'target_model', 'key', 'value', 'topic', 'question'];
    for (const field of relevantFields) {
      if (input[field] !== undefined && input[field] !== null && input[field] !== '') {
        const val = input[field];
        if (typeof val === 'string') return val;
        if (Array.isArray(val)) return val.join(', ');
        return JSON.stringify(val);
      }
    }

    // For objects with few keys, show them nicely
    const keys = Object.keys(input);
    if (keys.length <= 3) {
      return keys.map(k => {
        const v = input[k];
        if (typeof v === 'string') return `${k}: ${v}`;
        if (Array.isArray(v)) return `${k}: ${v.join(', ')}`;
        return `${k}: ${JSON.stringify(v)}`;
      }).join(', ');
    }

    // Fallback to simplified JSON
    return JSON.stringify(input);
  }

  return String(input);
}

// Format result for display
function formatResult(result: any): string {
  if (!result) return 'No result';
  if (typeof result === 'string') return result;

  // For objects, try to extract meaningful content
  if (typeof result === 'object') {
    // Handle error case
    if (result.error) {
      return `Error: ${result.error}`;
    }

    // Common result field names
    const relevantFields = ['result', 'content', 'response', 'data', 'output', 'message', 'summary', 'new_model', 'sections'];
    for (const field of relevantFields) {
      if (result[field]) {
        return typeof result[field] === 'string' ? result[field] : JSON.stringify(result[field], null, 2);
      }
    }

    // For success flags with additional info
    if (result.success !== undefined) {
      const extras = Object.entries(result)
        .filter(([k]) => k !== 'success')
        .map(([k, v]) => {
          if (typeof v === 'object' && v !== null) {
            return `${k}: ${JSON.stringify(v)}`;
          }
          return `${k}: ${v}`;
        })
        .join(', ');
      return extras || (result.success ? 'Success' : 'Failed');
    }

    // Fallback to JSON with formatting
    return JSON.stringify(result, null, 2);
  }

  return String(result);
}

// Memoized to prevent parent re-renders from affecting this component
// and to prevent typewriter glitches when expanding/collapsing
export const ToolCallBubble: React.FC<ToolCallBubbleProps> = React.memo(({
  toolName,
  input,
  result,
  status,
  accentColor,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const displayName = TOOL_DISPLAY_NAMES[toolName] || toolName.replace(/_/g, ' ');
  const inputText = formatInput(input, toolName);
  const resultText = formatResult(result);

  const isLoading = status === 'in_progress';
  const isFailed = status === 'failed';

  // Convert hex color to rgba for backgrounds
  const hexToRgba = (hex: string, alpha: number) => {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };

  return (
    <div
      className="mb-2 rounded-lg backdrop-blur-sm cursor-pointer transition-all duration-200 hover:brightness-110"
      style={{
        backgroundColor: hexToRgba(accentColor, 0.1),
        border: `1px solid ${hexToRgba(accentColor, 0.3)}`,
      }}
      onClick={() => !isLoading && setIsExpanded(!isExpanded)}
    >
      {/* Header row */}
      <div className="flex items-center justify-between px-3 py-2">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {/* Icon */}
          <span className="flex-shrink-0">
            {isLoading ? (
              <LoaderIcon size={14} color={accentColor} />
            ) : isFailed ? (
              <AlertIcon size={14} />
            ) : (
              <WrenchIcon size={14} color={accentColor} />
            )}
          </span>

          {/* Tool name */}
          <span
            className="text-xs font-medium flex-shrink-0"
            style={{ color: accentColor }}
          >
            {displayName}
          </span>
        </div>

        {/* Expand/collapse indicator */}
        {!isLoading && (
          <div className="flex-shrink-0 ml-2 text-text-tertiary">
            {isExpanded ? (
              <ChevronUpIcon size={14} />
            ) : (
              <ChevronDownIcon size={14} />
            )}
          </div>
        )}

        {/* Loading dots */}
        {isLoading && (
          <div className="flex gap-1 ml-2">
            <div
              className="w-1 h-1 rounded-full animate-pulse"
              style={{ backgroundColor: accentColor, animationDelay: '0ms' }}
            />
            <div
              className="w-1 h-1 rounded-full animate-pulse"
              style={{ backgroundColor: accentColor, animationDelay: '200ms' }}
            />
            <div
              className="w-1 h-1 rounded-full animate-pulse"
              style={{ backgroundColor: accentColor, animationDelay: '400ms' }}
            />
          </div>
        )}
      </div>

      {/* Expanded content */}
      {isExpanded && !isLoading && (
        <div
          className="px-3 pb-2 border-t"
          style={{ borderColor: hexToRgba(accentColor, 0.2) }}
        >
          {/* Full input */}
          {inputText && (
            <div className="mt-2">
              <span className="text-xs text-text-tertiary">Input: </span>
              <span className="text-xs text-text-secondary break-words">
                {inputText}
              </span>
            </div>
          )}

          {/* Result */}
          <div className="mt-1">
            <span className="text-xs text-text-tertiary">Result: </span>
            <span
              className={`text-xs break-words ${isFailed ? 'text-red-400' : 'text-text-secondary'}`}
              style={{
                display: 'block',
                maxHeight: '120px',
                overflowY: 'auto',
                whiteSpace: 'pre-wrap',
              }}
            >
              {truncateText(resultText, 500)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
});

export default ToolCallBubble;
