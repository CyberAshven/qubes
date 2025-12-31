export interface Qube {
  qube_id: string;
  name: string;
  genesis_prompt: string;
  ai_provider: string;
  ai_model: string;
  evaluation_model?: string;  // Model used for self-evaluation (separate from main model)
  voice_model?: string;
  tts_enabled?: boolean;  // Whether TTS (voice responses) is enabled
  creator?: string;
  birth_timestamp?: number;
  home_blockchain?: string;
  favorite_color: string;
  nft_category_id?: string;
  mint_txid?: string;
  avatar_url?: string;  // IPFS URL only (https://ipfs.io/ipfs/...) - use avatar_local_path for local files
  avatar_local_path?: string;  // Local file path for use with convertFileSrc()
  created_at: string;
  trust_score?: number;  // Average trust score across all relationships (0-100)
  memory_blocks_count?: number;
  block_breakdown?: Record<string, number>;  // Block counts by type (GENESIS, MESSAGE, THOUGHT, etc.)
  friends_count?: number;  // Number of friends (not just total relationships)
  total_relationships?: number;  // Total number of relationships
  best_friend?: string;  // Entity ID of best friend
  close_friends?: number;  // Number of close friends
  acquaintances?: number;  // Number of acquaintances
  strangers?: number;  // Number of strangers
  highest_trust?: number;  // Highest trust score among relationships (0-100)
  lowest_trust?: number;  // Lowest trust score among relationships (0-100)
  total_messages_sent?: number;  // Total messages sent across all relationships
  total_messages_received?: number;  // Total messages received across all relationships
  total_collaborations?: number;  // Total collaborations across all relationships
  successful_joint_tasks?: number;  // Successful joint tasks
  failed_joint_tasks?: number;  // Failed joint tasks
  avg_reliability?: number;  // Average reliability score (0-100)
  avg_honesty?: number;  // Average honesty score (0-100)
  avg_responsiveness?: number;  // Average responsiveness score (0-100)
  avg_compatibility?: number;  // Average compatibility score (0-100)
  status: 'active' | 'inactive' | 'busy';
  // Additional blockchain metadata
  recipient_address?: string;  // BCH address that owns this NFT
  public_key?: string;  // Public key of the Qube
  genesis_block_hash?: string;  // Hash of the genesis block
  commitment?: string;  // NFT commitment hash
  bcmr_uri?: string;  // IPFS URI for BCMR metadata
  avatar_ipfs_cid?: string;  // IPFS CID for avatar
  network?: string;  // mainnet or testnet
}

export type Tab = 'dashboard' | 'blocks' | 'qubes' | 'relationships' | 'skills' | 'economy' | 'settings' | 'connections';

export interface QubeSelectionState {
  activeQubeId: string | null;
  selectedQubeIds: string[];
  currentTab: Tab;
}

// Skill System Types
export type SkillTier = 'novice' | 'intermediate' | 'advanced' | 'expert';
export type SkillNodeType = 'avatar' | 'sun' | 'planet' | 'moon';

export interface SkillCategory {
  id: string;
  name: string;
  color: string;
  icon: string;
}

export interface Skill {
  id: string;
  name: string;
  description: string;
  category: string;  // Category ID
  nodeType: SkillNodeType;
  tier: SkillTier;
  level: number;  // 1-100
  xp: number;
  maxXP: number;  // 1000 for sun, 500 for planets, 250 for moons
  unlocked: boolean;
  prerequisite?: string;  // Skill ID of required skill
  toolCallReward?: string;  // Tool call unlocked when skill is maxed
  evidence: (string | { block_id: string; description?: string; xp_gained?: number })[];  // Block IDs or detailed evidence objects
  parentSkill?: string;  // For planets/moons, the parent skill ID
  icon?: string;  // Emoji/icon for planets and moons
}

export interface SkillTreeNode {
  id: string;
  type: SkillNodeType;
  data: Skill | QubeAvatarData;
  position: { x: number; y: number };
  orbitRadius?: number;
  orbitSpeed?: number;
  orbitAngle?: number;
}

export interface QubeAvatarData {
  qubeId: string;
  name: string;
  avatarUrl?: string;
  favoriteColor: string;
}

export interface SkillData {
  skills: Skill[];
  categories: SkillCategory[];
  lastUpdated: string;
}

// Audio Visualizer Types
export type WaveformStyle = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11;
export type ColorTheme = 'qube-color' | 'rainbow' | 'neon-cyan' | 'electric-purple' | 'matrix-green' | 'fire' | 'ice';
export type GradientStyle = 'solid' | 'gradient-dark' | 'gradient-complementary' | 'gradient-analogous';
export type AnimationSmoothness = 'low' | 'medium' | 'high' | 'ultra';

export interface VisualizerSettings {
  enabled: boolean;               // Can be toggled with V key
  waveform_style: WaveformStyle;  // 1-11 (F1-F11)
  color_theme: ColorTheme;        // Color scheme for visualization
  gradient_style: GradientStyle;  // Gradient variant when using qube-color
  sensitivity: number;            // 0-100 (default: 50)
  animation_smoothness: AnimationSmoothness;  // Performance/quality trade-off
  audio_offset_ms: number;        // -500 to +500 (default: 0)
  frequency_range: number;        // 1-100 (default: 20) - percentage of frequency spectrum to use
  output_monitor: number;         // 0 = main window overlay, 1+ = external monitor index
  last_updated?: string;          // ISO timestamp
}

export interface WaveformStyleInfo {
  value: WaveformStyle;
  label: string;
  icon: string;
  description: string;
}

export interface ColorThemeInfo {
  value: ColorTheme;
  label: string;
  icon?: string;
  color?: string;
  hasGradientOptions: boolean;
}

// Minting Payment Types
export interface MintingPaymentInfo {
  address: string;
  amount_bch: number;
  amount_satoshis: number;
  payment_uri: string;
  qr_data: string;
  op_return_data?: string;
  op_return_hex?: string;
}

export interface PendingMintingResult {
  success: boolean;
  error?: string;
  qube_id?: string;
  registration_id?: string;
  payment?: MintingPaymentInfo;
  websocket_url?: string;
  expires_at?: string;
  expires_in_seconds?: number;
  qube_name?: string;
}

export type MintingStatus = 'pending' | 'paid' | 'minting' | 'complete' | 'failed' | 'expired';

export interface MintingStatusResult {
  success: boolean;
  error?: string;
  status?: MintingStatus;
  registration_id?: string;
  category_id?: string;
  mint_txid?: string;
  bcmr_ipfs_cid?: string;
  error_message?: string;
  qube?: {
    qube_id: string;
    name: string;
    nft_category_id?: string;
    mint_txid?: string;
  };
}

export interface PendingRegistration {
  qube_id: string;
  registration_id: string;
  payment_address: string;
  payment_amount_bch: number;
  payment_amount_satoshis: number;
  payment_uri: string;
  qr_data: string;
  websocket_url: string;
  expires_at: string;
  expires_in_seconds: number;
  op_return_data?: string;
  op_return_hex?: string;
  created_at: string;
}

// NFT Authentication Types
export interface NftAuthResult {
  success: boolean;
  authenticated?: boolean;
  qube_id?: string;
  public_key?: string;
  category_id?: string;
  nft_verified?: boolean;
  token?: string;
  token_expires_at?: number;
  error?: string;
}

export interface NftAuthToken {
  qube_id: string;
  token: string;
  expires_at: number;
}

export interface NftAuthStatusResult {
  success: boolean;
  qube_id?: string;
  registered?: boolean;
  can_authenticate?: boolean;
  has_nft?: boolean;
  category_id?: string;
  error?: string;
}
