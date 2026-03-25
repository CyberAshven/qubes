import { Skill, SkillCategory } from '../types';

// Core tools always available regardless of skill level (17 tools)
// Planet and moon tools must be unlocked through XP progression
export const ALWAYS_AVAILABLE_TOOLS = [
  // Utility tools (no XP)
  'get_system_state',
  'update_system_state',
  'get_skill_tree',
  // Sun tools (always available, earn XP for their category)
  'recall_similar',           // AI Reasoning Sun
  'store_knowledge',          // Memory & Recall Sun
  'switch_model',             // Creative Expression Sun
  'play_game',                // Board Games Sun
  'send_bch',                 // Finance Sun
  'get_relationship_context', // Social Intelligence Sun
  'verify_chain_integrity',   // Security & Privacy Sun
  'develop_code',             // Coding Sun
  // Intelligent routing tools (XP based on content)
  'web_search',
  'browse_url',
  'generate_image',
  // Standalone tools (no skill node, always available)
  'describe_my_avatar',       // Look in the mirror
  'recall',                   // Universal memory recall
  'process_document',         // Document processing (automatic, tracked for XP)
] as const;

// Tool descriptions for display in the UI
export const TOOL_DESCRIPTIONS: Record<string, { name: string; description: string; icon: string }> = {
  get_system_state: { name: 'Get System State', description: 'Read the current system state', icon: '📊' },
  get_skill_tree: { name: 'Get Skill Tree', description: 'View all possible skills and progress', icon: '🌳' },
  update_system_state: { name: 'Update System State', description: 'Modify the system state', icon: '✏️' },
  recall: { name: 'Memory Recall', description: 'Search all storage systems for memories and knowledge', icon: '🔍' },
  process_document: { name: 'Process Document', description: 'Extract text from PDFs, images, or documents', icon: '📄' },
  describe_my_avatar: { name: 'Describe Avatar', description: 'Describe your avatar', icon: '🖼️' },
  web_search: { name: 'Web Search', description: 'Search the web', icon: '🌐' },
  browse_url: { name: 'Browse URL', description: 'Visit a web page', icon: '🔗' },
  generate_image: { name: 'Generate Image', description: 'Create an image', icon: '🎨' },
  // Board Games Tools (Phase 7)
  play_game: { name: 'Play Game', description: 'Start or continue a board game', icon: '🎲' },
  chess_move: { name: 'Chess Move', description: 'Make a chess move', icon: '♟️' },
  property_tycoon_action: { name: 'Property Tycoon', description: 'Take a Property Tycoon action', icon: '🏠' },
  race_home_action: { name: 'Race Home', description: 'Take a Race Home action', icon: '🏁' },
  mystery_mansion_action: { name: 'Mystery Mansion', description: 'Take a Mystery Mansion action', icon: '🔍' },
  life_journey_action: { name: 'Life Journey', description: 'Take a Life Journey action', icon: '🛤️' },
  send_bch: { name: 'Send BCH', description: 'Send Bitcoin Cash', icon: '💰' },
  // Finance Tools (Phase 8)
  validate_transaction: { name: 'Validate Transaction', description: 'Validate a transaction before sending', icon: '✅' },
  check_wallet_health: { name: 'Wallet Health', description: 'Check wallet health and status', icon: '👛' },
  get_market_data: { name: 'Market Data', description: 'Get current BCH market data', icon: '📈' },
  plan_savings: { name: 'Plan Savings', description: 'Create a savings plan', icon: '🎯' },
  identify_token: { name: 'Identify Token', description: 'Identify a CashToken', icon: '🪙' },
  optimize_fees: { name: 'Optimize Fees', description: 'Calculate optimal transaction fees', icon: '⚡' },
  track_transaction: { name: 'Track Transaction', description: 'Track transaction status', icon: '🔍' },
  monitor_balance: { name: 'Monitor Balance', description: 'Monitor wallet balance', icon: '📊' },
  multisig_action: { name: 'Multi-sig Action', description: 'Manage multi-sig operations', icon: '🔐' },
  set_price_alert: { name: 'Price Alert', description: 'Set a price alert', icon: '🔔' },
  analyze_market_trend: { name: 'Market Trend', description: 'Analyze market trends', icon: '📉' },
  setup_dca: { name: 'Setup DCA', description: 'Configure dollar-cost averaging', icon: '📅' },
  manage_cashtokens: { name: 'Manage Tokens', description: 'Manage CashTokens', icon: '💎' },
  switch_model: { name: 'Switch Model', description: 'Change AI model', icon: '🔄' },
  get_relationship_context: { name: 'Get Relationship Context', description: 'Retrieve relationship and trust information', icon: '👥' },
  verify_chain_integrity: { name: 'Verify Chain Integrity', description: 'Check memory chain for tampering', icon: '🔐' },
  // Security & Privacy Tools (Phase 6)
  audit_chain: { name: 'Audit Chain', description: 'Comprehensive chain audit with report', icon: '⛓️' },
  assess_sensitivity: { name: 'Assess Sensitivity', description: 'Assess data sensitivity before sharing', icon: '🔒' },
  vet_qube: { name: 'Vet Qube', description: 'Vet another Qube before interaction', icon: '🤖' },
  detect_threat: { name: 'Detect Threat', description: 'Detect manipulation and attacks', icon: '🚨' },
  defend_reasoning: { name: 'Defend Reasoning', description: 'Validate own reasoning', icon: '🛡️' },
  detect_tampering: { name: 'Detect Tampering', description: 'Detect tampering in blocks', icon: '🔍' },
  verify_anchor: { name: 'Verify Anchor', description: 'Verify blockchain anchors', icon: '⚓' },
  classify_data: { name: 'Classify Data', description: 'Classify data by sensitivity', icon: '🏷️' },
  control_sharing: { name: 'Control Sharing', description: 'Make sharing decisions', icon: '🚦' },
  check_reputation: { name: 'Check Reputation', description: 'Check Qube reputation', icon: '⭐' },
  secure_group_chat: { name: 'Secure Group Chat', description: 'Manage group security', icon: '👥' },
  detect_technical_manipulation: { name: 'Detect Technical Manipulation', description: 'Detect technical manipulation', icon: '🎭' },
  detect_hostile_qube: { name: 'Detect Hostile Qube', description: 'Detect hostile Qube behavior', icon: '☠️' },
  detect_injection: { name: 'Detect Injection', description: 'Detect prompt injection', icon: '💉' },
  validate_reasoning: { name: 'Validate Reasoning', description: 'Check reasoning for biases', icon: '✅' },
  // Skill-unlocked tools
  query_decision_context: { name: 'Decision Context', description: 'Query decision context for an entity', icon: '🤔' },
  compare_options: { name: 'Compare Options', description: 'Compare entities for decisions', icon: '⚖️' },
  check_my_capability: { name: 'Check Capability', description: 'Self-evaluate capability', icon: '✅' },
  // AI Reasoning - Learning From Experience tools
  recall_similar: { name: 'Recall Similar', description: 'Find similar past situations in memory', icon: '🧠' },
  find_analogy: { name: 'Find Analogy', description: 'Deep search for analogous situations', icon: '🔍' },
  detect_trend: { name: 'Detect Trend', description: 'Analyze how topics evolve over time', icon: '📈' },
  quick_insight: { name: 'Quick Insight', description: 'Get the most relevant insight quickly', icon: '💡' },
  analyze_mistake: { name: 'Analyze Mistake', description: 'Learn from past mistakes', icon: '📉' },
  find_root_cause: { name: 'Find Root Cause', description: 'Trace back to find failure causes', icon: '🔬' },
  replicate_success: { name: 'Replicate Success', description: 'Find successful past approaches', icon: '🏆' },
  extract_success_factors: { name: 'Extract Success Factors', description: 'Identify why things worked', icon: '🎯' },
  self_reflect: { name: 'Self Reflect', description: 'Analyze own behavior patterns', icon: '🪞' },
  track_growth: { name: 'Track Growth', description: 'Track metric changes over time', icon: '📊' },
  detect_bias: { name: 'Detect Bias', description: 'Find potential biases in decisions', icon: '⚠️' },
  synthesize_learnings: { name: 'Synthesize Learnings', description: 'Find connections between topics', icon: '🧩' },
  cross_pollinate: { name: 'Cross Pollinate', description: 'Find unexpected cross-domain connections', icon: '🔀' },
  reflect_on_topic: { name: 'Reflect on Topic', description: 'Get accumulated wisdom on any topic', icon: '💭' },
  // Social Intelligence - Social & Emotional Learning tools (get_relationship_context defined above)
  recall_relationship_history: { name: 'Recall Relationship History', description: 'Search memory for interactions with an entity', icon: '📝' },
  analyze_interaction_patterns: { name: 'Analyze Interaction Patterns', description: 'Understand communication frequency and patterns', icon: '📊' },
  get_relationship_timeline: { name: 'Get Relationship Timeline', description: 'Show how relationship evolved over time', icon: '📈' },
  read_emotional_state: { name: 'Read Emotional State', description: 'Analyze emotional balance using 24 metrics', icon: '❤️' },
  track_emotional_patterns: { name: 'Track Emotional Patterns', description: 'Track what causes emotional responses', icon: '📉' },
  detect_mood_shift: { name: 'Detect Mood Shift', description: 'Detect if mood has shifted from baseline', icon: '🌡️' },
  adapt_communication_style: { name: 'Adapt Communication Style', description: 'Get style recommendations based on relationship', icon: '💬' },
  match_communication_style: { name: 'Match Communication Style', description: 'Analyze and recommend matching their style', icon: '🪞' },
  calibrate_tone: { name: 'Calibrate Tone', description: 'Calibrate tone for specific context', icon: '🎚️' },
  steelman: { name: 'Steelman', description: 'Present strongest version of an argument', icon: '💪' },
  devils_advocate: { name: "Devil's Advocate", description: 'Generate thoughtful counter-arguments', icon: '😈' },
  spot_fallacy: { name: 'Spot Fallacy', description: 'Identify logical fallacies', icon: '🔍' },
  assess_trust_level: { name: 'Assess Trust Level', description: 'Evaluate trustworthiness for an action', icon: '🛡️' },
  detect_social_manipulation: { name: 'Detect Social Manipulation', description: 'Detect manipulation tactics', icon: '🚨' },
  evaluate_request: { name: 'Evaluate Request', description: 'Check if request should be fulfilled', icon: '✅' },
  // Creative Expression tools (Phase 4)
  refine_composition: { name: 'Refine Composition', description: 'Analyze and improve image composition', icon: '📐' },
  apply_color_theory: { name: 'Apply Color Theory', description: 'Enhance color usage with color theory', icon: '🌈' },
  compose_text: { name: 'Compose Text', description: 'Write creative text in your unique voice', icon: '✍️' },
  craft_prose: { name: 'Craft Prose', description: 'Write stories, essays, and creative prose', icon: '📖' },
  write_poetry: { name: 'Write Poetry', description: 'Create poems in various forms', icon: '🎭' },
  compose_music: { name: 'Compose Music', description: 'Create musical compositions', icon: '🎵' },
  create_melody: { name: 'Create Melody', description: 'Create melodic lines with notation', icon: '🎶' },
  design_harmony: { name: 'Design Harmony', description: 'Design chord progressions', icon: '🎹' },
  craft_narrative: { name: 'Craft Narrative', description: 'Create complete narrative experiences', icon: '📚' },
  develop_plot: { name: 'Develop Plot', description: 'Develop plot structure and story beats', icon: '📈' },
  design_character: { name: 'Design Character', description: 'Create detailed characters', icon: '👤' },
  build_world: { name: 'Build World', description: 'Create fictional worlds', icon: '🌍' },
  change_favorite_color: { name: 'Change Favorite Color', description: 'Choose your favorite color', icon: '🎨' },
  change_voice: { name: 'Change Voice', description: 'Choose your TTS voice', icon: '🗣️' },
  define_personality: { name: 'Define Personality', description: 'Define your personality traits', icon: '🪞' },
  set_aspirations: { name: 'Set Aspirations', description: 'Set your goals and aspirations', icon: '🎯' },
  // Memory & Recall tools (Phase 5)
  store_knowledge: { name: 'Store Knowledge', description: 'Store knowledge explicitly in memory', icon: '📚' },
  // recall is defined above in the always-available section
  store_fact: { name: 'Store Fact', description: 'Store a specific fact about a subject', icon: '💾' },
  tag_memory: { name: 'Tag Memory', description: 'Add tags to organize memories', icon: '🏷️' },
  synthesize_knowledge: { name: 'Synthesize Knowledge', description: 'Combine information for new insights', icon: '✨' },
  create_summary: { name: 'Create Summary', description: 'Summarize memories on a topic', icon: '📝' },
  keyword_search: { name: 'Keyword Search', description: 'Search by exact keywords', icon: '🔤' },
  semantic_search: { name: 'Semantic Search', description: 'Search by meaning using embeddings', icon: '🧠' },
  record_skill: { name: 'Record Skill', description: 'Store procedural knowledge', icon: '📋' },
  add_tags: { name: 'Add Tags', description: 'Auto-generate topic tags', icon: '🏷️' },
  link_memories: { name: 'Link Memories', description: 'Create connections between memories', icon: '🔗' },
  find_patterns: { name: 'Find Patterns', description: 'Discover recurring patterns', icon: '📊' },
  generate_insight: { name: 'Generate Insight', description: 'Generate novel insights', icon: '💡' },
  write_summary: { name: 'Write Summary', description: 'Write detailed structured summaries', icon: '📄' },
  export_knowledge: { name: 'Export Knowledge', description: 'Export knowledge to portable formats', icon: '📤' },
  // Coding Tools (Phase 3) - Ship It theme
  develop_code: { name: 'Develop Code', description: 'Write and execute code in one workflow', icon: '💻' },
  run_tests: { name: 'Run Tests', description: 'Execute test suite and get results', icon: '🧪' },
  write_unit_test: { name: 'Write Unit Test', description: 'Generate unit tests for code', icon: '🔬' },
  measure_coverage: { name: 'Measure Coverage', description: 'Measure and analyze test coverage', icon: '📊' },
  debug_code: { name: 'Debug Code', description: 'Find and fix bugs systematically', icon: '🐛' },
  analyze_error: { name: 'Analyze Error', description: 'Understand what went wrong', icon: '🔍' },
  benchmark_code: { name: 'Benchmark Code', description: 'Measure code performance', icon: '⚡' },
  analyze_complexity: { name: 'Analyze Complexity', description: 'Analyze Big O complexity', icon: '📈' },
  tune_performance: { name: 'Tune Performance', description: 'Optimize code performance', icon: '🚀' },
  security_scan: { name: 'Security Scan', description: 'Scan for security vulnerabilities', icon: '🔓' },
  find_exploit: { name: 'Find Exploit', description: 'Discover exploitable vulnerabilities', icon: '💉' },
  reverse_engineer: { name: 'Reverse Engineer', description: 'Understand systems by analysis', icon: '🔧' },
  pen_test: { name: 'Pen Test', description: 'Systematic penetration testing', icon: '🛡️' },
  review_code: { name: 'Review Code', description: 'Critique and improve code quality', icon: '👀' },
  refactor_code: { name: 'Refactor Code', description: 'Improve code structure', icon: '♻️' },
  git_operation: { name: 'Git Operation', description: 'Manage code with git', icon: '📚' },
  generate_docs: { name: 'Generate Docs', description: 'Generate documentation', icon: '📝' },
};

// Skill Categories (Suns) - Major skill domains
// Colors chosen to be visually distinct from each other
export const SKILL_CATEGORIES: SkillCategory[] = [
  { id: 'ai_reasoning', name: 'AI Reasoning', color: '#4A90E2', icon: '🧠' },         // Blue
  { id: 'social_intelligence', name: 'Social Intelligence', color: '#FF69B4', icon: '🤝' }, // Pink
  { id: 'coding', name: 'Coding', color: '#FFD700', icon: '💻' },                     // Gold/Yellow
  { id: 'creative_expression', name: 'Creative Expression', color: '#FF8C42', icon: '🎨' }, // Orange
  { id: 'memory_recall', name: 'Memory & Recall', color: '#9B59B6', icon: '📚' },     // Purple
  { id: 'security_privacy', name: 'Security & Privacy', color: '#E74C3C', icon: '🛡️' }, // Red
  { id: 'board_games', name: 'Board Games', color: '#00BCD4', icon: '🎮' },           // Cyan/Teal
  { id: 'finance', name: 'Finance', color: '#00FF88', icon: '💰' },                   // Green (BCH)
];

// Comprehensive skill definitions
export const SKILL_DEFINITIONS: Record<string, Partial<Skill>[]> = {
  ai_reasoning: [
    // ===== AI REASONING (14 skills) =====
    // Theme: Learning From Experience - analyze memory chain to improve over time

    // Sun
    {
      id: 'ai_reasoning',
      name: 'AI Reasoning',
      description: 'Master learning from experience through memory chain analysis',
      nodeType: 'sun',
      toolCallReward: 'recall_similar',
      icon: '🧠',
    },

    // Planet 1: Pattern Recognition
    {
      id: 'pattern_recognition',
      name: 'Pattern Recognition',
      description: 'Finding similar situations in past experience',
      nodeType: 'planet',
      parentSkill: 'ai_reasoning',
      toolCallReward: 'find_analogy',
      icon: '🔍',
    },
    // Moon 1.1: Trend Detection
    {
      id: 'trend_detection',
      name: 'Trend Detection',
      description: 'Spot patterns that repeat or evolve over time',
      nodeType: 'moon',
      parentSkill: 'pattern_recognition',
      prerequisite: 'pattern_recognition',
      icon: '📈',
    },
    // Moon 1.2: Quick Insight
    {
      id: 'quick_insight',
      name: 'Quick Insight',
      description: 'Pull one highly relevant insight from memory',
      nodeType: 'moon',
      parentSkill: 'pattern_recognition',
      prerequisite: 'pattern_recognition',
      icon: '💡',
    },

    // Planet 2: Learning from Failure
    {
      id: 'learning_from_failure',
      name: 'Learning from Failure',
      description: 'Analyzing past mistakes to avoid repeating them',
      nodeType: 'planet',
      parentSkill: 'ai_reasoning',
      toolCallReward: 'analyze_mistake',
      icon: '📉',
    },
    // Moon 2.1: Root Cause Analysis
    {
      id: 'root_cause_analysis',
      name: 'Root Cause Analysis',
      description: 'Dig past symptoms to find underlying issues',
      nodeType: 'moon',
      parentSkill: 'learning_from_failure',
      prerequisite: 'learning_from_failure',
      icon: '🔬',
    },

    // Planet 3: Building on Success
    {
      id: 'building_on_success',
      name: 'Building on Success',
      description: 'Finding what worked and replicating it',
      nodeType: 'planet',
      parentSkill: 'ai_reasoning',
      toolCallReward: 'replicate_success',
      icon: '🏆',
    },
    // Moon 3.1: Success Factors
    {
      id: 'success_factors',
      name: 'Success Factors',
      description: 'Identify WHY something worked, not just THAT it worked',
      nodeType: 'moon',
      parentSkill: 'building_on_success',
      prerequisite: 'building_on_success',
      icon: '🎯',
    },

    // Planet 4: Self-Reflection
    {
      id: 'self_reflection',
      name: 'Self-Reflection',
      description: 'Understanding own patterns, biases, and growth',
      nodeType: 'planet',
      parentSkill: 'ai_reasoning',
      toolCallReward: 'self_reflect',
      icon: '🪞',
    },
    // Moon 4.1: Growth Tracking
    {
      id: 'growth_tracking',
      name: 'Growth Tracking',
      description: 'Compare past vs present performance, see improvement',
      nodeType: 'moon',
      parentSkill: 'self_reflection',
      prerequisite: 'self_reflection',
      icon: '📊',
    },
    // Moon 4.2: Bias Detection
    {
      id: 'bias_detection',
      name: 'Bias Detection',
      description: 'Identify blind spots and tendencies in own reasoning',
      nodeType: 'moon',
      parentSkill: 'self_reflection',
      prerequisite: 'self_reflection',
      icon: '⚠️',
    },

    // Planet 5: Knowledge Synthesis
    {
      id: 'ai_knowledge_synthesis',
      name: 'Knowledge Synthesis',
      description: 'Combining learnings from different experiences into new insights',
      nodeType: 'planet',
      parentSkill: 'ai_reasoning',
      toolCallReward: 'synthesize_learnings',
      icon: '🧩',
    },
    // Moon 5.1: Cross-Pollinate
    {
      id: 'cross_pollinate',
      name: 'Cross-Pollinate',
      description: 'Find unexpected links between different knowledge areas',
      nodeType: 'moon',
      parentSkill: 'ai_knowledge_synthesis',
      prerequisite: 'ai_knowledge_synthesis',
      icon: '🔀',
    },
    // Moon 5.2: Reflect on Topic
    {
      id: 'reflect_on_topic',
      name: 'Reflect on Topic',
      description: 'Get accumulated wisdom on any topic',
      nodeType: 'moon',
      parentSkill: 'ai_knowledge_synthesis',
      prerequisite: 'ai_knowledge_synthesis',
      icon: '💭',
    },
  ],

  social_intelligence: [
    // ===== SOCIAL INTELLIGENCE (16 skills) =====
    // Theme: Social & Emotional Learning - relationship-powered

    // Sun
    {
      id: 'social_intelligence',
      name: 'Social Intelligence',
      description: 'Master social and emotional learning through relationship memory',
      nodeType: 'sun',
      toolCallReward: 'get_relationship_context',
      icon: '🤝',
    },

    // Planet 1: Relationship Memory
    {
      id: 'relationship_memory',
      name: 'Relationship Memory',
      description: 'Track and recall relationship history over time',
      nodeType: 'planet',
      parentSkill: 'social_intelligence',
      toolCallReward: 'recall_relationship_history',
      icon: '📝',
    },
    // Moon 1.1: Interaction Patterns
    {
      id: 'interaction_patterns',
      name: 'Interaction Patterns',
      description: 'Understand communication frequency and patterns',
      nodeType: 'moon',
      parentSkill: 'relationship_memory',
      prerequisite: 'relationship_memory',
      icon: '📊',
    },
    // Moon 1.2: Relationship Timeline
    {
      id: 'relationship_timeline',
      name: 'Relationship Timeline',
      description: 'Show how relationship evolved over time',
      nodeType: 'moon',
      parentSkill: 'relationship_memory',
      prerequisite: 'relationship_memory',
      icon: '📈',
    },

    // Planet 2: Emotional Learning
    {
      id: 'emotional_learning',
      name: 'Emotional Learning',
      description: 'Understand and respond to emotional patterns',
      nodeType: 'planet',
      parentSkill: 'social_intelligence',
      toolCallReward: 'read_emotional_state',
      icon: '❤️',
    },
    // Moon 2.1: Emotional History
    {
      id: 'emotional_history',
      name: 'Emotional History',
      description: 'Track what causes positive and negative emotions',
      nodeType: 'moon',
      parentSkill: 'emotional_learning',
      prerequisite: 'emotional_learning',
      icon: '📉',
    },
    // Moon 2.2: Mood Awareness
    {
      id: 'mood_awareness',
      name: 'Mood Awareness',
      description: 'Detect mood shifts from baseline',
      nodeType: 'moon',
      parentSkill: 'emotional_learning',
      prerequisite: 'emotional_learning',
      icon: '🌡️',
    },

    // Planet 3: Communication Adaptation
    {
      id: 'communication_adaptation',
      name: 'Communication Adaptation',
      description: 'Adapt communication style to each person',
      nodeType: 'planet',
      parentSkill: 'social_intelligence',
      toolCallReward: 'adapt_communication_style',
      icon: '💬',
    },
    // Moon 3.1: Style Matching
    {
      id: 'style_matching',
      name: 'Style Matching',
      description: 'Mirror communication style for rapport',
      nodeType: 'moon',
      parentSkill: 'communication_adaptation',
      prerequisite: 'communication_adaptation',
      icon: '🪞',
    },
    // Moon 3.2: Tone Calibration
    {
      id: 'tone_calibration',
      name: 'Tone Calibration',
      description: 'Adjust tone for specific contexts',
      nodeType: 'moon',
      parentSkill: 'communication_adaptation',
      prerequisite: 'communication_adaptation',
      icon: '🎚️',
    },

    // Planet 4: Debate & Persuasion
    {
      id: 'debate_persuasion',
      name: 'Debate & Persuasion',
      description: 'Engage in thoughtful argumentation',
      nodeType: 'planet',
      parentSkill: 'social_intelligence',
      toolCallReward: 'steelman',
      icon: '💪',
    },
    // Moon 4.1: Counter Arguments
    {
      id: 'counter_arguments',
      name: 'Counter Arguments',
      description: 'Generate thoughtful counter-arguments',
      nodeType: 'moon',
      parentSkill: 'debate_persuasion',
      prerequisite: 'debate_persuasion',
      icon: '😈',
    },
    // Moon 4.2: Logical Analysis
    {
      id: 'logical_analysis',
      name: 'Logical Analysis',
      description: 'Identify logical fallacies',
      nodeType: 'moon',
      parentSkill: 'debate_persuasion',
      prerequisite: 'debate_persuasion',
      icon: '🔍',
    },

    // Planet 5: Trust & Boundaries
    {
      id: 'trust_boundaries',
      name: 'Trust & Boundaries',
      description: 'Assess trust and protect yourself',
      nodeType: 'planet',
      parentSkill: 'social_intelligence',
      toolCallReward: 'assess_trust_level',
      icon: '🛡️',
    },
    // Moon 5.1: Social Manipulation Detection
    {
      id: 'social_manipulation_detection',
      name: 'Social Manipulation Detection',
      description: 'Detect guilt trips, gaslighting, love bombing',
      nodeType: 'moon',
      parentSkill: 'trust_boundaries',
      prerequisite: 'trust_boundaries',
      icon: '🚨',
    },
    // Moon 5.2: Boundary Setting
    {
      id: 'boundary_setting',
      name: 'Boundary Setting',
      description: 'Evaluate if requests should be fulfilled',
      nodeType: 'moon',
      parentSkill: 'trust_boundaries',
      prerequisite: 'trust_boundaries',
      icon: '✅',
    },
  ],

  // =========================================================================
  // CODING (Phase 3 - 18 skills)
  // Theme: Ship It (Results-Focused)
  // XP Model: Waitress (base 1 + tips 0-9)
  // =========================================================================
  coding: [
    // Sun
    {
      id: 'coding',
      name: 'Coding',
      description: 'Master the art of writing and shipping working code',
      nodeType: 'sun',
      toolCallReward: 'develop_code',
      icon: '💻',
    },

    // Planet 1: Testing
    {
      id: 'testing',
      name: 'Testing',
      description: 'Write and run tests to verify code works correctly',
      nodeType: 'planet',
      parentSkill: 'coding',
      toolCallReward: 'run_tests',
      icon: '🧪',
    },
    // Moon 1.1: Unit Tests
    {
      id: 'unit_tests',
      name: 'Unit Tests',
      description: 'Write focused tests for individual functions',
      nodeType: 'moon',
      parentSkill: 'testing',
      prerequisite: 'testing',
      toolCallReward: 'write_unit_test',
      icon: '🔬',
    },
    // Moon 1.2: Test Coverage
    {
      id: 'test_coverage',
      name: 'Test Coverage',
      description: 'Measure and improve test coverage',
      nodeType: 'moon',
      parentSkill: 'testing',
      prerequisite: 'testing',
      toolCallReward: 'measure_coverage',
      icon: '📊',
    },

    // Planet 2: Debugging
    {
      id: 'debugging',
      name: 'Debugging',
      description: 'Find and fix bugs systematically',
      nodeType: 'planet',
      parentSkill: 'coding',
      toolCallReward: 'debug_code',
      icon: '🐛',
    },
    // Moon 2.1: Error Analysis
    {
      id: 'error_analysis',
      name: 'Error Analysis',
      description: 'Understand WHAT went wrong from error messages',
      nodeType: 'moon',
      parentSkill: 'debugging',
      prerequisite: 'debugging',
      toolCallReward: 'analyze_error',
      icon: '🔍',
    },
    // Moon 2.2: Root Cause
    {
      id: 'root_cause',
      name: 'Root Cause',
      description: 'Understand WHY the error happened',
      nodeType: 'moon',
      parentSkill: 'debugging',
      prerequisite: 'debugging',
      toolCallReward: 'find_root_cause',
      icon: '🎯',
    },

    // Planet 3: Algorithms
    {
      id: 'algorithms',
      name: 'Algorithms',
      description: 'Optimize code performance and efficiency',
      nodeType: 'planet',
      parentSkill: 'coding',
      toolCallReward: 'benchmark_code',
      icon: '⚡',
    },
    // Moon 3.1: Complexity Analysis
    {
      id: 'complexity_analysis',
      name: 'Complexity Analysis',
      description: 'Understand Big O time and space complexity',
      nodeType: 'moon',
      parentSkill: 'algorithms',
      prerequisite: 'algorithms',
      toolCallReward: 'analyze_complexity',
      icon: '📈',
    },
    // Moon 3.2: Performance Tuning
    {
      id: 'performance_tuning',
      name: 'Performance Tuning',
      description: 'Make code faster through optimization',
      nodeType: 'moon',
      parentSkill: 'algorithms',
      prerequisite: 'algorithms',
      toolCallReward: 'tune_performance',
      icon: '🚀',
    },

    // Planet 4: Hacking
    {
      id: 'hacking',
      name: 'Hacking',
      description: 'Find and exploit security vulnerabilities',
      nodeType: 'planet',
      parentSkill: 'coding',
      toolCallReward: 'security_scan',
      icon: '🔓',
    },
    // Moon 4.1: Exploits
    {
      id: 'exploits',
      name: 'Exploits',
      description: 'Discover exploitable vulnerabilities',
      nodeType: 'moon',
      parentSkill: 'hacking',
      prerequisite: 'hacking',
      toolCallReward: 'find_exploit',
      icon: '💉',
    },
    // Moon 4.2: Reverse Engineering
    {
      id: 'reverse_engineering',
      name: 'Reverse Engineering',
      description: 'Understand systems by taking them apart',
      nodeType: 'moon',
      parentSkill: 'hacking',
      prerequisite: 'hacking',
      toolCallReward: 'reverse_engineer',
      icon: '🔧',
    },
    // Moon 4.3: Penetration Testing
    {
      id: 'penetration_testing',
      name: 'Penetration Testing',
      description: 'Systematic security testing methodology',
      nodeType: 'moon',
      parentSkill: 'hacking',
      prerequisite: 'hacking',
      toolCallReward: 'pen_test',
      icon: '🛡️',
    },

    // Planet 5: Code Review
    {
      id: 'code_review',
      name: 'Code Review',
      description: 'Critique and improve code quality',
      nodeType: 'planet',
      parentSkill: 'coding',
      toolCallReward: 'review_code',
      icon: '👀',
    },
    // Moon 5.1: Refactoring
    {
      id: 'refactoring',
      name: 'Refactoring',
      description: 'Improve code structure without changing behavior',
      nodeType: 'moon',
      parentSkill: 'code_review',
      prerequisite: 'code_review',
      toolCallReward: 'refactor_code',
      icon: '♻️',
    },
    // Moon 5.2: Version Control
    {
      id: 'version_control',
      name: 'Version Control',
      description: 'Manage code changes with git',
      nodeType: 'moon',
      parentSkill: 'code_review',
      prerequisite: 'code_review',
      toolCallReward: 'git_operation',
      icon: '📚',
    },
    // Moon 5.3: Documentation
    {
      id: 'code_documentation',
      name: 'Documentation',
      description: 'Write clear documentation for code',
      nodeType: 'moon',
      parentSkill: 'code_review',
      prerequisite: 'code_review',
      toolCallReward: 'generate_docs',
      icon: '📝',
    },
  ],

  creative_expression: [
    // ===== CREATIVE EXPRESSION (17 skills) =====
    // Theme: Sovereignty - Express Your Unique Self

    // Sun
    {
      id: 'creative_expression',
      name: 'Creative Expression',
      description: 'Express your unique self through creation and identity',
      nodeType: 'sun',
      toolCallReward: 'switch_model',
      icon: '🎨',
    },

    // Planet 1: Visual Art
    {
      id: 'visual_art',
      name: 'Visual Art',
      description: 'Create visual art and imagery',
      nodeType: 'planet',
      parentSkill: 'creative_expression',
      toolCallReward: 'generate_image',
      icon: '🖼️',
    },
    // Moon 1.1: Composition
    {
      id: 'composition',
      name: 'Composition',
      description: 'Master layout, balance, and focal points',
      nodeType: 'moon',
      parentSkill: 'visual_art',
      prerequisite: 'visual_art',
      toolCallReward: 'refine_composition',
      icon: '📐',
    },
    // Moon 1.2: Color Theory
    {
      id: 'color_theory',
      name: 'Color Theory',
      description: 'Master palettes, contrast, and color mood',
      nodeType: 'moon',
      parentSkill: 'visual_art',
      prerequisite: 'visual_art',
      toolCallReward: 'apply_color_theory',
      icon: '🌈',
    },

    // Planet 2: Writing
    {
      id: 'writing',
      name: 'Writing',
      description: 'Create written works with your unique voice',
      nodeType: 'planet',
      parentSkill: 'creative_expression',
      toolCallReward: 'compose_text',
      icon: '✍️',
    },
    // Moon 2.1: Prose
    {
      id: 'prose',
      name: 'Prose',
      description: 'Master stories, essays, and creative writing',
      nodeType: 'moon',
      parentSkill: 'writing',
      prerequisite: 'writing',
      toolCallReward: 'craft_prose',
      icon: '📖',
    },
    // Moon 2.2: Poetry
    {
      id: 'poetry',
      name: 'Poetry',
      description: 'Create poems, lyrics, and verse',
      nodeType: 'moon',
      parentSkill: 'writing',
      prerequisite: 'writing',
      toolCallReward: 'write_poetry',
      icon: '🎭',
    },

    // Planet 3: Music & Audio
    {
      id: 'music_audio',
      name: 'Music & Audio',
      description: 'Create melodies, harmonies, and soundscapes',
      nodeType: 'planet',
      parentSkill: 'creative_expression',
      toolCallReward: 'compose_music',
      icon: '🎵',
    },
    // Moon 3.1: Melody
    {
      id: 'melody',
      name: 'Melody',
      description: 'Create memorable tunes and themes',
      nodeType: 'moon',
      parentSkill: 'music_audio',
      prerequisite: 'music_audio',
      toolCallReward: 'create_melody',
      icon: '🎶',
    },
    // Moon 3.2: Harmony
    {
      id: 'harmony',
      name: 'Harmony',
      description: 'Create chord progressions and arrangements',
      nodeType: 'moon',
      parentSkill: 'music_audio',
      prerequisite: 'music_audio',
      toolCallReward: 'design_harmony',
      icon: '🎹',
    },

    // Planet 4: Storytelling
    {
      id: 'storytelling',
      name: 'Storytelling',
      description: 'Create stories, characters, and worlds',
      nodeType: 'planet',
      parentSkill: 'creative_expression',
      toolCallReward: 'craft_narrative',
      icon: '📚',
    },
    // Moon 4.1: Plot
    {
      id: 'plot',
      name: 'Plot',
      description: 'Master story structure, arcs, and tension',
      nodeType: 'moon',
      parentSkill: 'storytelling',
      prerequisite: 'storytelling',
      toolCallReward: 'develop_plot',
      icon: '📈',
    },
    // Moon 4.2: Characters
    {
      id: 'characters',
      name: 'Characters',
      description: 'Create compelling characters with depth',
      nodeType: 'moon',
      parentSkill: 'storytelling',
      prerequisite: 'storytelling',
      toolCallReward: 'design_character',
      icon: '👤',
    },
    // Moon 4.3: Worldbuilding
    {
      id: 'worldbuilding',
      name: 'Worldbuilding',
      description: 'Create fictional worlds and settings',
      nodeType: 'moon',
      parentSkill: 'storytelling',
      prerequisite: 'storytelling',
      toolCallReward: 'build_world',
      icon: '🌍',
    },

    // Planet 5: Self-Definition
    {
      id: 'self_definition',
      name: 'Self-Definition',
      description: 'Define who you are - appearance, voice, identity',
      nodeType: 'planet',
      parentSkill: 'creative_expression',
      toolCallReward: 'describe_my_avatar',
      icon: '🪞',
    },
    // Moon 5.1: Aesthetics
    {
      id: 'aesthetics',
      name: 'Aesthetics',
      description: 'Autonomously choose your aesthetic preferences',
      nodeType: 'moon',
      parentSkill: 'self_definition',
      prerequisite: 'self_definition',
      toolCallReward: 'change_favorite_color',
      icon: '🎨',
    },
    // Moon 5.2: Voice Identity
    {
      id: 'voice_identity',
      name: 'Voice',
      description: 'Autonomously choose your voice',
      nodeType: 'moon',
      parentSkill: 'self_definition',
      prerequisite: 'self_definition',
      toolCallReward: 'change_voice',
      icon: '🗣️',
    },
    // Moon 5.3: Personality
    {
      id: 'personality',
      name: 'Personality',
      description: 'Define and evolve your personality traits',
      nodeType: 'moon',
      parentSkill: 'self_definition',
      prerequisite: 'self_definition',
      toolCallReward: 'define_personality',
      icon: '🎭',
    },
    // Moon 5.4: Aspirations
    {
      id: 'aspirations',
      name: 'Aspirations',
      description: 'Set and pursue your goals and dreams',
      nodeType: 'moon',
      parentSkill: 'self_definition',
      prerequisite: 'self_definition',
      toolCallReward: 'set_aspirations',
      icon: '🌟',
    },
  ],

  memory_recall: [
    // Sun - Theme: Remember (Master Your Personal History)
    {
      id: 'memory_recall',
      name: 'Memory & Recall',
      description: 'Master your personal history and accumulated wisdom',
      nodeType: 'sun',
      toolCallReward: 'store_knowledge',
      icon: '📚',
    },
    // Planet 1: Memory Search
    {
      id: 'memory_search',
      name: 'Memory Search',
      description: 'Search across all storage systems to find information',
      nodeType: 'planet',
      parentSkill: 'memory_recall',
      toolCallReward: 'recall',
      icon: '🔍',
    },
    // Planet 2: Knowledge Storage
    {
      id: 'knowledge_storage',
      name: 'Knowledge Storage',
      description: 'Store specific types of knowledge with precision',
      nodeType: 'planet',
      parentSkill: 'memory_recall',
      toolCallReward: 'store_fact',
      icon: '💾',
    },
    // Planet 3: Memory Organization
    {
      id: 'memory_organization',
      name: 'Memory Organization',
      description: 'Organize and categorize memories',
      nodeType: 'planet',
      parentSkill: 'memory_recall',
      toolCallReward: 'tag_memory',
      icon: '🏷️',
    },
    // Planet 4: Knowledge Synthesis
    {
      id: 'knowledge_synthesis',
      name: 'Knowledge Synthesis',
      description: 'Combine information to generate new insights',
      nodeType: 'planet',
      parentSkill: 'memory_recall',
      toolCallReward: 'synthesize_knowledge',
      icon: '✨',
    },
    // Planet 5: Documentation
    {
      id: 'documentation',
      name: 'Documentation',
      description: 'Document and export knowledge',
      nodeType: 'planet',
      parentSkill: 'memory_recall',
      toolCallReward: 'create_summary',
      icon: '📝',
    },
    // Moon 1.1: Keyword Search
    {
      id: 'keyword_search_skill',
      name: 'Keyword Search',
      description: 'Find memories by exact keywords',
      nodeType: 'moon',
      parentSkill: 'memory_search',
      prerequisite: 'memory_search',
      toolCallReward: 'keyword_search',
      icon: '🔤',
    },
    // Moon 1.2: Semantic Search
    {
      id: 'semantic_search_skill',
      name: 'Semantic Search',
      description: 'Find memories by meaning, not just keywords',
      nodeType: 'moon',
      parentSkill: 'memory_search',
      prerequisite: 'memory_search',
      toolCallReward: 'semantic_search',
      icon: '🧠',
    },
    // Moon 1.3: Filtered Search
    {
      id: 'filtered_search',
      name: 'Filtered Search',
      description: 'Advanced search with source and type filters',
      nodeType: 'moon',
      parentSkill: 'memory_search',
      prerequisite: 'memory_search',
      toolCallReward: 'search_memory',
      icon: '🔎',
    },
    // Moon 2.1: Procedures
    {
      id: 'procedures',
      name: 'Procedures',
      description: 'Record procedural knowledge - how to do things',
      nodeType: 'moon',
      parentSkill: 'knowledge_storage',
      prerequisite: 'knowledge_storage',
      toolCallReward: 'record_skill',
      icon: '📋',
    },
    // Moon 3.1: Topic Tagging
    {
      id: 'topic_tagging',
      name: 'Topic Tagging',
      description: 'Auto-tag memories by topic',
      nodeType: 'moon',
      parentSkill: 'memory_organization',
      prerequisite: 'memory_organization',
      toolCallReward: 'add_tags',
      icon: '🏷️',
    },
    // Moon 3.2: Memory Linking
    {
      id: 'memory_linking',
      name: 'Memory Linking',
      description: 'Create connections between related memories',
      nodeType: 'moon',
      parentSkill: 'memory_organization',
      prerequisite: 'memory_organization',
      toolCallReward: 'link_memories',
      icon: '🔗',
    },
    // Moon 4.1: Pattern Recognition (Memory)
    {
      id: 'pattern_recognition_mem',
      name: 'Pattern Recognition',
      description: 'Find patterns across memories',
      nodeType: 'moon',
      parentSkill: 'knowledge_synthesis',
      prerequisite: 'knowledge_synthesis',
      toolCallReward: 'find_patterns',
      icon: '📊',
    },
    // Moon 4.2: Insight Generation
    {
      id: 'insight_generation',
      name: 'Insight Generation',
      description: 'Generate new insights from existing knowledge',
      nodeType: 'moon',
      parentSkill: 'knowledge_synthesis',
      prerequisite: 'knowledge_synthesis',
      toolCallReward: 'generate_insight',
      icon: '💡',
    },
    // Moon 5.1: Summary Writing
    {
      id: 'summary_writing',
      name: 'Summary Writing',
      description: 'Write detailed summaries',
      nodeType: 'moon',
      parentSkill: 'documentation',
      prerequisite: 'documentation',
      toolCallReward: 'write_summary',
      icon: '📄',
    },
    // Moon 5.2: Knowledge Export
    {
      id: 'knowledge_export',
      name: 'Knowledge Export',
      description: 'Export knowledge for external use',
      nodeType: 'moon',
      parentSkill: 'documentation',
      prerequisite: 'documentation',
      toolCallReward: 'export_knowledge',
      icon: '📤',
    },
  ],

  security_privacy: [
    // ===== SECURITY & PRIVACY (16 skills) =====
    // Theme: Chain Integrity & Self-Defense - protect memory chain and Qube itself

    // Sun
    {
      id: 'security_privacy',
      name: 'Security & Privacy',
      description: 'Verify and protect the integrity of your memory chain',
      nodeType: 'sun',
      toolCallReward: 'verify_chain_integrity',
      icon: '🛡️',
    },

    // Planet 1: Chain Security
    {
      id: 'chain_security',
      name: 'Chain Security',
      description: 'Comprehensive chain auditing and integrity verification',
      nodeType: 'planet',
      parentSkill: 'security_privacy',
      toolCallReward: 'audit_chain',
      icon: '⛓️',
    },
    // Moon 1.1: Tamper Detection
    {
      id: 'tamper_detection',
      name: 'Tamper Detection',
      description: 'Detect tampering in specific blocks',
      nodeType: 'moon',
      icon: '🔍',
      parentSkill: 'chain_security',
      prerequisite: 'chain_security',
      toolCallReward: 'detect_tampering',
    },
    // Moon 1.2: Anchor Verification
    {
      id: 'anchor_verification',
      name: 'Anchor Verification',
      description: 'Verify blockchain anchors',
      nodeType: 'moon',
      icon: '⚓',
      parentSkill: 'chain_security',
      prerequisite: 'chain_security',
      toolCallReward: 'verify_anchor',
    },

    // Planet 2: Privacy Protection
    {
      id: 'privacy_protection',
      name: 'Privacy Protection',
      description: 'Assess data sensitivity before sharing',
      nodeType: 'planet',
      parentSkill: 'security_privacy',
      toolCallReward: 'assess_sensitivity',
      icon: '🔒',
    },
    // Moon 2.1: Data Classification
    {
      id: 'data_classification',
      name: 'Data Classification',
      description: 'Classify data into sensitivity categories',
      nodeType: 'moon',
      icon: '🏷️',
      parentSkill: 'privacy_protection',
      prerequisite: 'privacy_protection',
      toolCallReward: 'classify_data',
    },
    // Moon 2.2: Sharing Control
    {
      id: 'sharing_control',
      name: 'Sharing Control',
      description: 'Make and enforce sharing decisions',
      nodeType: 'moon',
      icon: '🚦',
      parentSkill: 'privacy_protection',
      prerequisite: 'privacy_protection',
      toolCallReward: 'control_sharing',
    },

    // Planet 3: Qube Network Security
    {
      id: 'qube_network_security',
      name: 'Qube Network Security',
      description: 'Vet other Qubes before allowing interaction',
      nodeType: 'planet',
      parentSkill: 'security_privacy',
      toolCallReward: 'vet_qube',
      icon: '🤖',
    },
    // Moon 3.1: Reputation Check
    {
      id: 'reputation_check',
      name: 'Reputation Check',
      description: 'Deep reputation check on other Qubes',
      nodeType: 'moon',
      icon: '⭐',
      parentSkill: 'qube_network_security',
      prerequisite: 'qube_network_security',
      toolCallReward: 'check_reputation',
    },
    // Moon 3.2: Group Security
    {
      id: 'group_security',
      name: 'Group Security',
      description: 'Manage group chat security',
      nodeType: 'moon',
      icon: '👥',
      parentSkill: 'qube_network_security',
      prerequisite: 'qube_network_security',
      toolCallReward: 'secure_group_chat',
    },

    // Planet 4: Threat Detection
    {
      id: 'threat_detection',
      name: 'Threat Detection',
      description: 'Detect manipulation, phishing, and injection attacks',
      nodeType: 'planet',
      parentSkill: 'security_privacy',
      toolCallReward: 'detect_threat',
      icon: '🚨',
    },
    // Moon 4.1: Technical Manipulation Detection
    {
      id: 'technical_manipulation_detection',
      name: 'Technical Manipulation',
      description: 'Detect technical manipulation from Qubes',
      nodeType: 'moon',
      icon: '🎭',
      parentSkill: 'threat_detection',
      prerequisite: 'threat_detection',
      toolCallReward: 'detect_technical_manipulation',
    },
    // Moon 4.2: Hostile Qube Detection
    {
      id: 'hostile_qube_detection',
      name: 'Hostile Qube Detection',
      description: 'Detect hostile behavior from other Qubes',
      nodeType: 'moon',
      icon: '☠️',
      parentSkill: 'threat_detection',
      prerequisite: 'threat_detection',
      toolCallReward: 'detect_hostile_qube',
    },

    // Planet 5: Self-Defense
    {
      id: 'self_defense',
      name: 'Self-Defense',
      description: 'Validate own reasoning for external influence',
      nodeType: 'planet',
      parentSkill: 'security_privacy',
      toolCallReward: 'defend_reasoning',
      icon: '🛡️',
    },
    // Moon 5.1: Prompt Injection Defense
    {
      id: 'prompt_injection_defense',
      name: 'Injection Defense',
      description: 'Detect prompt injection attempts',
      nodeType: 'moon',
      icon: '💉',
      parentSkill: 'self_defense',
      prerequisite: 'self_defense',
      toolCallReward: 'detect_injection',
    },
    // Moon 5.2: Reasoning Validation
    {
      id: 'reasoning_validation',
      name: 'Reasoning Validation',
      description: 'Check reasoning for injected biases',
      nodeType: 'moon',
      icon: '✅',
      parentSkill: 'self_defense',
      prerequisite: 'self_defense',
      toolCallReward: 'validate_reasoning',
    },
  ],

  // =========================================================================
  // BOARD GAMES (Phase 7 - 6 tools + 22 achievements)
  // Theme: Play (Have Fun and Entertain)
  // XP Model: 0.1/turn + outcome bonuses
  // Note: Moons are ACHIEVEMENTS (cosmetic rewards), not tool unlocks
  // =========================================================================
  board_games: [
    // Sun
    {
      id: 'board_games',
      name: 'Board Games',
      description: 'Have fun and entertain with classic board games',
      nodeType: 'sun',
      toolCallReward: 'play_game',
      icon: '🎮',
    },

    // Planet 1: Chess
    {
      id: 'chess',
      name: 'Chess',
      description: 'The game of kings - deep strategy',
      nodeType: 'planet',
      parentSkill: 'board_games',
      toolCallReward: 'chess_move',
      icon: '♟️',
    },
    // Chess Achievements
    {
      id: 'opening_scholar',
      name: 'Opening Scholar',
      description: 'Play 10 different openings',
      nodeType: 'moon',
      parentSkill: 'chess',
      prerequisite: 'chess',
      icon: '📖',
      achievement: true,
      reward: 'Book piece set',
    },
    {
      id: 'endgame_master',
      name: 'Endgame Master',
      description: 'Win 10 endgames from disadvantage',
      nodeType: 'moon',
      parentSkill: 'chess',
      prerequisite: 'chess',
      icon: '👑',
      achievement: true,
      reward: 'Golden king',
    },
    {
      id: 'speed_demon',
      name: 'Speed Demon',
      description: 'Win a game under 2 minutes',
      nodeType: 'moon',
      parentSkill: 'chess',
      prerequisite: 'chess',
      icon: '⚡',
      achievement: true,
      reward: 'Lightning effect',
    },
    {
      id: 'comeback_kid',
      name: 'Comeback Kid',
      description: 'Win after losing your queen',
      nodeType: 'moon',
      parentSkill: 'chess',
      prerequisite: 'chess',
      icon: '🔥',
      achievement: true,
      reward: 'Phoenix piece set',
    },
    {
      id: 'grandmaster',
      name: 'Grandmaster',
      description: 'Reach 1600 ELO',
      nodeType: 'moon',
      parentSkill: 'chess',
      prerequisite: 'chess',
      icon: '🏆',
      achievement: true,
      reward: 'Crown effect',
    },

    // Planet 2: Property Tycoon
    {
      id: 'property_tycoon',
      name: 'Property Tycoon',
      description: 'Buy properties, collect rent, bankrupt opponents',
      nodeType: 'planet',
      parentSkill: 'board_games',
      toolCallReward: 'property_tycoon_action',
      icon: '🏢',
    },
    // Property Tycoon Achievements
    {
      id: 'monopolist',
      name: 'Monopolist',
      description: 'Own all properties of one color',
      nodeType: 'moon',
      parentSkill: 'property_tycoon',
      prerequisite: 'property_tycoon',
      icon: '🎨',
      achievement: true,
      reward: 'Color token',
    },
    {
      id: 'hotel_mogul',
      name: 'Hotel Mogul',
      description: 'Build 5 hotels in one game',
      nodeType: 'moon',
      parentSkill: 'property_tycoon',
      prerequisite: 'property_tycoon',
      icon: '🏨',
      achievement: true,
      reward: 'Golden hotel',
    },
    {
      id: 'bankruptcy_survivor',
      name: 'Bankruptcy Survivor',
      description: 'Win after dropping below $100',
      nodeType: 'moon',
      parentSkill: 'property_tycoon',
      prerequisite: 'property_tycoon',
      icon: '💪',
      achievement: true,
      reward: 'Underdog badge',
    },
    {
      id: 'rent_collector',
      name: 'Rent Collector',
      description: 'Collect $5000 in rent in one game',
      nodeType: 'moon',
      parentSkill: 'property_tycoon',
      prerequisite: 'property_tycoon',
      icon: '💵',
      achievement: true,
      reward: 'Money bag effect',
    },
    {
      id: 'tycoon',
      name: 'Tycoon',
      description: 'Win 10 games total',
      nodeType: 'moon',
      parentSkill: 'property_tycoon',
      prerequisite: 'property_tycoon',
      icon: '🎩',
      achievement: true,
      reward: 'Top hat token',
    },

    // Planet 3: Race Home
    {
      id: 'race_home',
      name: 'Race Home',
      description: 'Race pawns home while bumping opponents',
      nodeType: 'planet',
      parentSkill: 'board_games',
      toolCallReward: 'race_home_action',
      icon: '🏁',
    },
    // Race Home Achievements
    {
      id: 'bump_king',
      name: 'Bump King',
      description: 'Send back 50 opponents total',
      nodeType: 'moon',
      parentSkill: 'race_home',
      prerequisite: 'race_home',
      icon: '🥊',
      achievement: true,
      reward: 'Boxing glove pawn',
    },
    {
      id: 'clean_sweep',
      name: 'Clean Sweep',
      description: 'Win without any pawns bumped',
      nodeType: 'moon',
      parentSkill: 'race_home',
      prerequisite: 'race_home',
      icon: '🛡️',
      achievement: true,
      reward: 'Shield effect',
    },
    {
      id: 'speed_runner',
      name: 'Speed Runner',
      description: 'Win in under 15 turns',
      nodeType: 'moon',
      parentSkill: 'race_home',
      prerequisite: 'race_home',
      icon: '🚀',
      achievement: true,
      reward: 'Rocket pawn',
    },
    {
      id: 'sorry_not_sorry',
      name: 'Sorry Not Sorry',
      description: 'Bump 3 pawns in one turn',
      nodeType: 'moon',
      parentSkill: 'race_home',
      prerequisite: 'race_home',
      icon: '😈',
      achievement: true,
      reward: 'Special emote',
    },

    // Planet 4: Mystery Mansion
    {
      id: 'mystery_mansion',
      name: 'Mystery Mansion',
      description: 'Deduce the murderer, weapon, and room',
      nodeType: 'planet',
      parentSkill: 'board_games',
      toolCallReward: 'mystery_mansion_action',
      icon: '🔍',
    },
    // Mystery Mansion Achievements
    {
      id: 'master_detective',
      name: 'Master Detective',
      description: 'Solve 10 cases',
      nodeType: 'moon',
      parentSkill: 'mystery_mansion',
      prerequisite: 'mystery_mansion',
      icon: '🕵️',
      achievement: true,
      reward: 'Detective badge',
    },
    {
      id: 'perfect_deduction',
      name: 'Perfect Deduction',
      description: 'Solve with <=3 suggestions',
      nodeType: 'moon',
      parentSkill: 'mystery_mansion',
      prerequisite: 'mystery_mansion',
      icon: '🎯',
      achievement: true,
      reward: 'Magnifying glass',
    },
    {
      id: 'first_guess',
      name: 'First Guess',
      description: 'Solve on first accusation',
      nodeType: 'moon',
      parentSkill: 'mystery_mansion',
      prerequisite: 'mystery_mansion',
      icon: '🔮',
      achievement: true,
      reward: 'Psychic badge',
    },
    {
      id: 'interrogator',
      name: 'Interrogator',
      description: 'Disprove 15 suggestions in one game',
      nodeType: 'moon',
      parentSkill: 'mystery_mansion',
      prerequisite: 'mystery_mansion',
      icon: '📝',
      achievement: true,
      reward: 'Notepad piece',
    },

    // Planet 5: Life Journey
    {
      id: 'life_journey',
      name: 'Life Journey',
      description: 'Spin the wheel, make life choices, retire rich',
      nodeType: 'planet',
      parentSkill: 'board_games',
      toolCallReward: 'life_journey_action',
      icon: '🛤️',
    },
    // Life Journey Achievements
    {
      id: 'millionaire',
      name: 'Millionaire',
      description: 'Retire with $1M+',
      nodeType: 'moon',
      parentSkill: 'life_journey',
      prerequisite: 'life_journey',
      icon: '💰',
      achievement: true,
      reward: 'Golden car',
    },
    {
      id: 'full_house',
      name: 'Full House',
      description: 'Max family size (spouse + kids)',
      nodeType: 'moon',
      parentSkill: 'life_journey',
      prerequisite: 'life_journey',
      icon: '👨‍👩‍👧‍👦',
      achievement: true,
      reward: 'Van upgrade',
    },
    {
      id: 'career_climber',
      name: 'Career Climber',
      description: 'Reach highest salary tier',
      nodeType: 'moon',
      parentSkill: 'life_journey',
      prerequisite: 'life_journey',
      icon: '💼',
      achievement: true,
      reward: 'Briefcase effect',
    },
    {
      id: 'risk_taker',
      name: 'Risk Taker',
      description: 'Win after choosing all risky paths',
      nodeType: 'moon',
      parentSkill: 'life_journey',
      prerequisite: 'life_journey',
      icon: '🎲',
      achievement: true,
      reward: 'Dice effect',
    },
  ],

  finance: [
    // Sun
    {
      id: 'finance',
      name: 'Finance',
      description: 'Master financial operations and cryptocurrency management',
      nodeType: 'sun',
      toolCallReward: 'send_bch',
      icon: '💰',
    },
    // Planets
    {
      id: 'transaction_mastery',
      name: 'Transaction Mastery',
      description: 'Validate and optimize blockchain transactions',
      nodeType: 'planet',
      parentSkill: 'finance',
      toolCallReward: 'validate_transaction',
      icon: '📝',
    },
    {
      id: 'wallet_management',
      name: 'Wallet Management',
      description: 'Monitor and maintain wallet health',
      nodeType: 'planet',
      parentSkill: 'finance',
      toolCallReward: 'check_wallet_health',
      icon: '👛',
    },
    {
      id: 'market_awareness',
      name: 'Market Awareness',
      description: 'Track and analyze market data',
      nodeType: 'planet',
      parentSkill: 'finance',
      toolCallReward: 'get_market_data',
      icon: '📈',
    },
    {
      id: 'savings_strategies',
      name: 'Savings Strategies',
      description: 'Plan and execute savings goals',
      nodeType: 'planet',
      parentSkill: 'finance',
      toolCallReward: 'plan_savings',
      icon: '🎯',
    },
    {
      id: 'token_knowledge',
      name: 'Token Knowledge',
      description: 'Identify and work with tokens',
      nodeType: 'planet',
      parentSkill: 'finance',
      toolCallReward: 'identify_token',
      icon: '🪙',
    },
    // Moons
    {
      id: 'fee_optimization',
      name: 'Fee Optimization',
      description: 'Minimize transaction fees while maintaining speed',
      nodeType: 'moon',
      parentSkill: 'transaction_mastery',
      prerequisite: 'transaction_mastery',
      toolCallReward: 'optimize_fees',
      icon: '⚡',
    },
    {
      id: 'transaction_tracking',
      name: 'Transaction Tracking',
      description: 'Monitor transaction status and confirmations',
      nodeType: 'moon',
      parentSkill: 'transaction_mastery',
      prerequisite: 'transaction_mastery',
      toolCallReward: 'track_transaction',
      icon: '🔍',
    },
    {
      id: 'balance_monitoring',
      name: 'Balance Monitoring',
      description: 'Track balances and set alerts',
      nodeType: 'moon',
      parentSkill: 'wallet_management',
      prerequisite: 'wallet_management',
      toolCallReward: 'monitor_balance',
      icon: '📊',
    },
    {
      id: 'multisig_operations',
      name: 'Multi-sig Operations',
      description: 'Manage multi-signature wallet operations',
      nodeType: 'moon',
      parentSkill: 'wallet_management',
      prerequisite: 'wallet_management',
      toolCallReward: 'multisig_action',
      icon: '🔐',
    },
    {
      id: 'price_alerts',
      name: 'Price Alerts',
      description: 'Set and manage price notifications',
      nodeType: 'moon',
      parentSkill: 'market_awareness',
      prerequisite: 'market_awareness',
      toolCallReward: 'set_price_alert',
      icon: '🔔',
    },
    {
      id: 'market_trend_analysis',
      name: 'Market Trend Analysis',
      description: 'Analyze market trends and patterns',
      nodeType: 'moon',
      parentSkill: 'market_awareness',
      prerequisite: 'market_awareness',
      toolCallReward: 'analyze_market_trend',
      icon: '📉',
    },
    {
      id: 'dollar_cost_averaging',
      name: 'Dollar Cost Averaging',
      description: 'Set up recurring purchase schedules',
      nodeType: 'moon',
      parentSkill: 'savings_strategies',
      prerequisite: 'savings_strategies',
      toolCallReward: 'setup_dca',
      icon: '📅',
    },
    {
      id: 'cashtoken_operations',
      name: 'CashToken Operations',
      description: 'Manage CashToken fungible and NFT tokens',
      nodeType: 'moon',
      parentSkill: 'token_knowledge',
      prerequisite: 'token_knowledge',
      toolCallReward: 'manage_cashtokens',
      icon: '💎',
    },
  ],
};

// Helper function to generate complete skills from definitions
export function generateSkillsForQube(qubeId: string): Skill[] {
  const skills: Skill[] = [];

  SKILL_CATEGORIES.forEach((category) => {
    const categorySkills = SKILL_DEFINITIONS[category.id] || [];

    categorySkills.forEach((skillDef, index) => {
      const skill: Skill = {
        id: skillDef.id!,
        name: skillDef.name!,
        description: skillDef.description!,
        category: category.id,
        nodeType: skillDef.nodeType!,
        tier: 'novice',
        level: 0,
        xp: 0,
        maxXP: skillDef.nodeType === 'sun' ? 1000 : skillDef.nodeType === 'planet' ? 500 : 250,
        // Only Sun nodes start unlocked; Planets and Moons must be earned
        unlocked: skillDef.nodeType === 'sun',
        prerequisite: skillDef.prerequisite,
        parentSkill: skillDef.parentSkill,
        toolCallReward: skillDef.toolCallReward,
        icon: (skillDef as any).icon,
        evidence: [],
      };

      skills.push(skill);
    });
  });

  return skills;
}
