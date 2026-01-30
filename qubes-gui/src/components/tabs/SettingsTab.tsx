import { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { GlassCard, GlassButton, GlassInput } from '../glass';
import { useAuth } from '../../hooks/useAuth';
import { useChainState } from '../../contexts/ChainStateContext';
import { useUpdater } from '../../hooks/useUpdater';
import { useQubeSelection } from '../../hooks/useQubeSelection';
import { VoiceSettingsPanel } from '../settings/VoiceSettingsPanel';

interface APIKeyStatus {
  provider: string;
  configured: boolean;
  masked_value?: string;
  validated?: boolean;
  validation_message?: string;
}

interface ValidationResult {
  valid: boolean;
  message: string;
  details?: any;
}

interface BlockPreferences {
  individual_auto_anchor: boolean;
  individual_anchor_threshold: number;
  group_auto_anchor: boolean;
  group_anchor_threshold: number;
  auto_sync_ipfs_on_anchor: boolean;
}

interface RelationshipSettings {
  difficulty: 'quick' | 'normal' | 'long' | 'extreme';
  description: string;
}

interface DifficultyPreset {
  name: string;
  description: string;
  min_interactions: {
    acquaintance: number;
    friend: number;
    close_friend: number;
    best_friend: number;
  };
}

interface DecisionConfig {
  trust_threshold: number;
  expertise_threshold: number;
  collaboration_threshold: number;
  confidence_threshold: number;
  humility_threshold: number;
  metric_influence: number;
  validation_strictness: number;
  max_antagonism: number;
  max_distrust: number;
  max_betrayal: number;
  enable_auto_temperature: boolean;
  enable_validation_layer: boolean;
  enable_metric_tools: boolean;
  auto_thresholds: boolean;
}

interface MemoryConfig {
  recall_threshold: number;
  max_recalls: number;
  decay_rate: number;
  semantic_weight: number;
  keyword_weight: number;
  temporal_weight: number;
  relationship_weight: number;
}

export const SettingsTab: React.FC = () => {
  const { userId, password, autoLockEnabled, autoLockTimeout, setAutoLockSettings } = useAuth();
  const { invalidateCache, loadChainState } = useChainState();

  const {
    updateAvailable,
    updateStatus,
    isChecking,
    isDownloading,
    downloadProgress,
    error: updateError,
    checkForUpdates,
    installUpdate,
    dismissUpdate,
  } = useUpdater(true); // Check for updates on mount

  // Get selected qube from roster for per-qube settings
  const { selectionByTab } = useQubeSelection();
  const selectedQubeIdForSettings = selectionByTab.settings?.[0] || null;

  const [apiKeys, setApiKeys] = useState<Record<string, string>>({
    openai: '',
    anthropic: '',
    google: '',
    deepseek: '',
    perplexity: '',
    venice: '',
    nanogpt: '',
    pinata_jwt: '',
    elevenlabs: '',
    deepgram: '',
  });

  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [loadingKeys, setLoadingKeys] = useState(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [validatingKey, setValidatingKey] = useState<string | null>(null);
  const [keyStatuses, setKeyStatuses] = useState<Record<string, APIKeyStatus>>({});

  // Block preferences state
  const [blockPreferences, setBlockPreferences] = useState<BlockPreferences>({
    individual_auto_anchor: true,
    individual_anchor_threshold: 10,
    group_auto_anchor: true,
    group_anchor_threshold: 5,
    auto_sync_ipfs_on_anchor: false,
  });
  const [loadingPreferences, setLoadingPreferences] = useState(true);
  const [savingPreferences, setSavingPreferences] = useState(false);

  // Relationship settings state
  const [relationshipSettings, setRelationshipSettings] = useState<RelationshipSettings>({
    difficulty: 'long',
    description: 'Relationships take years to develop, making them truly meaningful'
  });
  const [loadingRelationshipSettings, setLoadingRelationshipSettings] = useState(true);
  const [savingRelationshipSettings, setSavingRelationshipSettings] = useState(false);
  const [difficultyPresets, setDifficultyPresets] = useState<Record<string, DifficultyPreset>>({});

  // Local input state (for typing without triggering API calls)
  const [individualThresholdInput, setIndividualThresholdInput] = useState('10');
  const [groupThresholdInput, setGroupThresholdInput] = useState('5');

  // Google TTS credentials path state
  const [googleTTSPath, setGoogleTTSPath] = useState('');
  const [loadingGoogleTTSPath, setLoadingGoogleTTSPath] = useState(true);
  const [savingGoogleTTSPath, setSavingGoogleTTSPath] = useState(false);

  // Decision intelligence config state
  const [decisionConfig, setDecisionConfig] = useState<DecisionConfig>({
    trust_threshold: 70,
    expertise_threshold: 60,
    collaboration_threshold: 65,
    confidence_threshold: 60,
    humility_threshold: 70,
    metric_influence: 70,
    validation_strictness: 50,
    max_antagonism: 30,
    max_distrust: 40,
    max_betrayal: 10,
    enable_auto_temperature: true,
    enable_validation_layer: true,
    enable_metric_tools: true,
    auto_thresholds: false,
  });
  const [loadingDecisionConfig, setLoadingDecisionConfig] = useState(true);
  const [savingDecisionConfig, setSavingDecisionConfig] = useState(false);

  // Trust personality state
  const [availableQubes, setAvailableQubes] = useState<Array<{ qube_id: string; name: string }>>([]);
  const [selectedQubeForTrust, setSelectedQubeForTrust] = useState<string>('');
  const [trustPersonality, setTrustPersonality] = useState<'cautious' | 'balanced' | 'social' | 'analytical'>('balanced');
  const [loadingTrustPersonality, setLoadingTrustPersonality] = useState(false);
  const [savingTrustPersonality, setSavingTrustPersonality] = useState(false);

  // Memory recall config state
  const [memoryConfig, setMemoryConfig] = useState<MemoryConfig>({
    recall_threshold: 15.0,
    max_recalls: 5,
    decay_rate: 0.1,
    semantic_weight: 0.4,
    keyword_weight: 0.3,
    temporal_weight: 0.15,
    relationship_weight: 0.1,
  });
  // Local state for smooth slider dragging (synced on release)
  const [localMemoryConfig, setLocalMemoryConfig] = useState<MemoryConfig>({
    recall_threshold: 15.0,
    max_recalls: 5,
    decay_rate: 0.1,
    semantic_weight: 0.4,
    keyword_weight: 0.3,
    temporal_weight: 0.15,
    relationship_weight: 0.1,
  });
  const [loadingMemoryConfig, setLoadingMemoryConfig] = useState(true);
  const [savingMemoryConfig, setSavingMemoryConfig] = useState(false);
  const [showAdvancedRecall, setShowAdvancedRecall] = useState(false);

  // Collapsible panel state (all collapsed by default)
  const [collapsedPanels, setCollapsedPanels] = useState<Record<string, boolean>>({
    apiKeys: true,
    googleTTS: true,
    blockSettings: true,
    blockRecall: true,
    relationshipDifficulty: true,
    trustPersonality: true,
    voiceSettings: true,
    decisionIntelligence: true,
    security: true,
    softwareUpdates: true,
  });

  const togglePanel = (panel: string) => {
    setCollapsedPanels(prev => ({ ...prev, [panel]: !prev[panel] }));
  };

  const providerLabels: Record<string, string> = {
    openai: 'OpenAI',
    anthropic: 'Anthropic (Claude)',
    google: 'Google AI (Gemini)',
    deepseek: 'DeepSeek',
    perplexity: 'Perplexity',
    venice: 'Venice (Private AI)',
    nanogpt: 'NanoGPT (Pay-per-prompt)',
    pinata_jwt: 'Pinata IPFS',
    elevenlabs: 'ElevenLabs (TTS)',
    deepgram: 'Deepgram (STT)',
  };

  const providerPlaceholders: Record<string, string> = {
    openai: 'sk-...',
    anthropic: 'sk-ant-...',
    google: 'AIza...',
    deepseek: 'sk-...',
    perplexity: 'pplx-...',
    venice: '...',
    nanogpt: '...',
    pinata_jwt: 'eyJ...',
    elevenlabs: '...',
    deepgram: '...',
  };

  // Load API keys on mount
  useEffect(() => {
    loadConfiguredKeys();
  }, [userId]);

  // Load block preferences on mount
  useEffect(() => {
    loadBlockPreferences();
  }, [userId]);

  // Load relationship settings on mount
  useEffect(() => {
    loadRelationshipSettings();
  }, [userId]);

  // Load Google TTS path on mount
  useEffect(() => {
    loadGoogleTTSPath();
  }, [userId]);

  // Load decision config on mount
  useEffect(() => {
    loadDecisionConfig();
  }, [userId]);

  // Load available qubes on mount
  useEffect(() => {
    loadAvailableQubes();
  }, [userId]);

  // Load trust personality when selected qube changes
  useEffect(() => {
    if (selectedQubeForTrust) {
      loadTrustPersonality(selectedQubeForTrust);
    }
  }, [selectedQubeForTrust]);

  // Load memory config on mount
  useEffect(() => {
    loadMemoryConfig();
  }, [userId]);

  const loadGoogleTTSPath = async () => {
    try {
      setLoadingGoogleTTSPath(true);
      const result = await invoke<{ path: string | null }>('get_google_tts_path', {
        userId,
      });
      setGoogleTTSPath(result.path || '');
    } catch (error) {
      console.error('Failed to load Google TTS path:', error);
    } finally {
      setLoadingGoogleTTSPath(false);
    }
  };

  const handleSaveGoogleTTSPath = async () => {
    try {
      setSavingGoogleTTSPath(true);
      await invoke('set_google_tts_path', {
        userId,
        path: googleTTSPath.trim() === '' ? 'none' : googleTTSPath,
      });
      alert('✅ Google TTS credentials path saved');
    } catch (error) {
      console.error('Failed to save Google TTS path:', error);
      alert(`❌ Error saving path: ${String(error)}`);
    } finally {
      setSavingGoogleTTSPath(false);
    }
  };

  const loadDecisionConfig = async () => {
    try {
      setLoadingDecisionConfig(true);
      const result = await invoke<{ success: boolean; config: DecisionConfig }>('get_decision_config', {
        userId,
      });
      if (result.success && result.config) {
        setDecisionConfig(result.config);
      }
    } catch (error) {
      console.error('Failed to load decision config:', error);
    } finally {
      setLoadingDecisionConfig(false);
    }
  };

  const handleDecisionConfigChange = async (updates: Partial<DecisionConfig>) => {
    try {
      setSavingDecisionConfig(true);
      const newConfig = { ...decisionConfig, ...updates };
      setDecisionConfig(newConfig);

      await invoke('update_decision_config', {
        userId,
        configJson: JSON.stringify(updates),
      });
    } catch (error) {
      console.error('Failed to update decision config:', error);
      alert(`❌ Error updating config: ${String(error)}`);
      // Reload to get the correct state
      await loadDecisionConfig();
    } finally {
      setSavingDecisionConfig(false);
    }
  };

  const loadMemoryConfig = async () => {
    try {
      setLoadingMemoryConfig(true);
      const result = await invoke<{ success: boolean; config: MemoryConfig }>('get_memory_config', {
        userId,
      });
      if (result.success && result.config) {
        setMemoryConfig(result.config);
        setLocalMemoryConfig(result.config); // Sync local state
      }
    } catch (error) {
      console.error('Failed to load memory config:', error);
    } finally {
      setLoadingMemoryConfig(false);
    }
  };

  // Update local state while dragging (no API call)
  const handleMemoryConfigSliderChange = (updates: Partial<MemoryConfig>) => {
    setLocalMemoryConfig(prev => ({ ...prev, ...updates }));
  };

  // Save to backend when slider is released
  const handleMemoryConfigSliderRelease = async () => {
    // Find what changed between memoryConfig and localMemoryConfig
    const updates: Partial<MemoryConfig> = {};
    for (const key of Object.keys(localMemoryConfig) as (keyof MemoryConfig)[]) {
      if (localMemoryConfig[key] !== memoryConfig[key]) {
        (updates as any)[key] = localMemoryConfig[key];
      }
    }

    if (Object.keys(updates).length === 0) return; // Nothing changed

    try {
      setSavingMemoryConfig(true);
      setMemoryConfig(localMemoryConfig); // Update main state

      await invoke('update_memory_config', {
        userId,
        configJson: JSON.stringify(updates),
      });
    } catch (error) {
      console.error('Failed to update memory config:', error);
      alert(`❌ Error updating config: ${String(error)}`);
      // Reload to get the correct state
      await loadMemoryConfig();
    } finally {
      setSavingMemoryConfig(false);
    }
  };

  const loadAvailableQubes = async () => {
    try {
      const qubes = await invoke<any[]>('list_qubes', { userId, password });
      setAvailableQubes(qubes.map(q => ({
        qube_id: q.qube_id,
        name: q.name
      })));
      if (qubes.length > 0) {
        setSelectedQubeForTrust(qubes[0].qube_id);
      }
    } catch (error) {
      console.error('Failed to load qubes:', error);
    }
  };

  const loadTrustPersonality = async (qubeId: string) => {
    if (!qubeId || !password) return;
    try {
      setLoadingTrustPersonality(true);
      const result = await invoke<{ trust_profile: string }>('get_trust_personality', {
        userId,
        qubeId,
        password
      });
      setTrustPersonality(result.trust_profile as any || 'balanced');
    } catch (error) {
      console.error('Failed to load trust personality:', error);
      setTrustPersonality('balanced');
    } finally {
      setLoadingTrustPersonality(false);
    }
  };

  const handleTrustPersonalityChange = async (personality: 'cautious' | 'balanced' | 'social' | 'analytical') => {
    if (!selectedQubeForTrust) return;
    try {
      setSavingTrustPersonality(true);
      setTrustPersonality(personality);

      await invoke('update_trust_personality', {
        userId,
        qubeId: selectedQubeForTrust,
        trustProfile: personality
      });

      // Invalidate and refresh chain state cache
      invalidateCache(selectedQubeForTrust);
      await loadChainState(selectedQubeForTrust, true);

      alert(`✅ Trust personality updated to "${personality}"`);
    } catch (error) {
      console.error('Failed to update trust personality:', error);
      alert(`❌ Error updating trust personality: ${String(error)}`);
      // Reload to get correct state
      await loadTrustPersonality(selectedQubeForTrust);
    } finally {
      setSavingTrustPersonality(false);
    }
  };

  const loadConfiguredKeys = async () => {
    try {
      setLoadingKeys(true);
      const result = await invoke<{ providers: string[] }>('get_configured_api_keys', {
        userId,
        password,
      });

      const statuses: Record<string, APIKeyStatus> = {};
      for (const provider of Object.keys(apiKeys)) {
        statuses[provider] = {
          provider,
          configured: result.providers.includes(provider),
          validated: undefined,
        };
      }

      setKeyStatuses(statuses);
    } catch (error) {
      console.error('Failed to load configured keys:', error);
    } finally {
      setLoadingKeys(false);
    }
  };

  const handleKeyChange = (provider: string, value: string) => {
    console.log(`[API Key] handleKeyChange called for ${provider}, value length: ${value?.length || 0}`);
    setApiKeys(prev => ({ ...prev, [provider]: value }));

    // Clear validation status when user changes the key
    setKeyStatuses(prev => ({
      ...prev,
      [provider]: {
        ...prev[provider],
        validated: undefined,
        validation_message: undefined,
      },
    }));
  };

  const toggleShowKey = (provider: string) => {
    setShowKeys(prev => ({ ...prev, [provider]: !prev[provider] }));
  };

  const handleSaveKey = async (provider: string) => {
    const apiKey = apiKeys[provider];
    if (!apiKey || !apiKey.trim()) {
      alert('Please enter an API key');
      return;
    }

    try {
      setSavingKey(provider);
      const result = await invoke<{ success: boolean; error?: string }>('save_api_key', {
        userId,
        provider,
        apiKey,
        password,
      });

      if (result.success) {
        // Update status
        setKeyStatuses(prev => ({
          ...prev,
          [provider]: {
            ...prev[provider],
            configured: true,
          },
        }));

        // Clear input field
        setApiKeys(prev => ({ ...prev, [provider]: '' }));

        alert(`✅ ${providerLabels[provider]} API key saved successfully`);
      } else {
        alert(`❌ Failed to save API key: ${result.error}`);
      }
    } catch (error) {
      console.error('Failed to save API key:', error);
      alert(`❌ Error saving API key: ${String(error)}`);
    } finally {
      setSavingKey(null);
    }
  };

  const handleValidateKey = async (provider: string) => {
    const apiKey = apiKeys[provider];
    const isConfigured = keyStatuses[provider]?.configured;

    // If input field is empty but key is configured, test the saved key
    if ((!apiKey || !apiKey.trim()) && !isConfigured) {
      alert('Please enter an API key to validate');
      return;
    }

    try {
      setValidatingKey(provider);

      // If testing a saved key (input is empty), pass password to decrypt
      const testingSavedKey = !apiKey || !apiKey.trim();

      const result = await invoke<ValidationResult>('validate_api_key', {
        userId,
        provider,
        apiKey: apiKey || '__SAVED__', // Use placeholder to indicate testing saved key
        password: testingSavedKey ? password : undefined, // Pass password only for saved keys
      });

      setKeyStatuses(prev => ({
        ...prev,
        [provider]: {
          ...prev[provider],
          validated: result.valid,
          validation_message: result.message,
        },
      }));

      if (result.valid) {
        alert(`✅ ${providerLabels[provider]}: ${result.message}`);
      } else {
        alert(`❌ ${providerLabels[provider]}: ${result.message}`);
      }
    } catch (error) {
      console.error('Failed to validate API key:', error);
      alert(`❌ Error validating API key: ${String(error)}`);

      setKeyStatuses(prev => ({
        ...prev,
        [provider]: {
          ...prev[provider],
          validated: false,
          validation_message: String(error),
        },
      }));
    } finally {
      setValidatingKey(null);
    }
  };

  const handleDeleteKey = async (provider: string) => {
    if (!confirm(`Are you sure you want to delete the ${providerLabels[provider]} API key?`)) {
      return;
    }

    try {
      const result = await invoke<{ success: boolean; error?: string }>('delete_api_key', {
        userId,
        provider,
        password,
      });

      if (result.success) {
        setKeyStatuses(prev => ({
          ...prev,
          [provider]: {
            ...prev[provider],
            configured: false,
            validated: undefined,
            validation_message: undefined,
          },
        }));

        alert(`✅ ${providerLabels[provider]} API key deleted`);
      } else {
        alert(`❌ Failed to delete API key: ${result.error}`);
      }
    } catch (error) {
      console.error('Failed to delete API key:', error);
      alert(`❌ Error deleting API key: ${String(error)}`);
    }
  };

  const loadBlockPreferences = async () => {
    try {
      setLoadingPreferences(true);
      const prefs = await invoke<BlockPreferences>('get_block_preferences', {
        userId,
      });
      setBlockPreferences(prefs);
      // Update local input state
      setIndividualThresholdInput(prefs.individual_anchor_threshold.toString());
      setGroupThresholdInput(prefs.group_anchor_threshold.toString());
    } catch (error) {
      console.error('Failed to load block preferences:', error);
    } finally {
      setLoadingPreferences(false);
    }
  };

  const handleToggleChange = async (
    field: 'individual_auto_anchor' | 'group_auto_anchor' | 'auto_sync_ipfs_on_anchor',
    value: boolean
  ) => {
    try {
      setSavingPreferences(true);

      // Optimistically update UI
      setBlockPreferences(prev => ({ ...prev, [field]: value }));

      const result = await invoke<BlockPreferences>('update_block_preferences', {
        userId,
        individualAutoAnchor: field === 'individual_auto_anchor' ? value : undefined,
        groupAutoAnchor: field === 'group_auto_anchor' ? value : undefined,
        autoSyncIpfsOnAnchor: field === 'auto_sync_ipfs_on_anchor' ? value : undefined,
      });

      // Update with server response
      setBlockPreferences(result);

      // Invalidate cache for all qubes since this is a user-level preference
      for (const qube of availableQubes) {
        invalidateCache(qube.qube_id);
      }
      // Force refresh for all qubes
      for (const qube of availableQubes) {
        loadChainState(qube.qube_id, true);
      }
    } catch (error) {
      console.error('Failed to update preference:', error);
      alert(`❌ Error updating preference: ${String(error)}`);
      await loadBlockPreferences();
    } finally {
      setSavingPreferences(false);
    }
  };

  const handleThresholdBlur = async (
    field: 'individual_anchor_threshold' | 'group_anchor_threshold',
    inputValue: string
  ) => {
    const parsed = parseInt(inputValue) || 5;
    const value = Math.max(5, Math.min(50, parsed));

    // Don't save if value hasn't changed
    if (value === blockPreferences[field]) {
      return;
    }

    try {
      setSavingPreferences(true);

      const result = await invoke<BlockPreferences>('update_block_preferences', {
        userId,
        individualAnchorThreshold: field === 'individual_anchor_threshold' ? value : undefined,
        groupAnchorThreshold: field === 'group_anchor_threshold' ? value : undefined,
      });

      // Update with server response
      setBlockPreferences(result);
      setIndividualThresholdInput(result.individual_anchor_threshold.toString());
      setGroupThresholdInput(result.group_anchor_threshold.toString());

      // Invalidate cache for all qubes since this is a user-level preference
      for (const qube of availableQubes) {
        invalidateCache(qube.qube_id);
      }
      // Force refresh for all qubes
      for (const qube of availableQubes) {
        loadChainState(qube.qube_id, true);
      }
    } catch (error) {
      console.error('Failed to update preference:', error);
      alert(`❌ Error updating preference: ${String(error)}`);
      await loadBlockPreferences();
    } finally {
      setSavingPreferences(false);
    }
  };

  const loadRelationshipSettings = async () => {
    try {
      setLoadingRelationshipSettings(true);

      // Load current difficulty setting
      const settings = await invoke<RelationshipSettings>('get_relationship_difficulty', {
        userId,
      });
      setRelationshipSettings(settings);

      // Load all difficulty presets for display
      const presets = await invoke<Record<string, DifficultyPreset>>('get_difficulty_presets');
      setDifficultyPresets(presets);
    } catch (error) {
      console.error('Failed to load relationship settings:', error);
      // Set default if error
      setRelationshipSettings({
        difficulty: 'long',
        description: 'Relationships take years to develop, making them truly meaningful'
      });
    } finally {
      setLoadingRelationshipSettings(false);
    }
  };

  const handleDifficultyChange = async (difficulty: 'quick' | 'normal' | 'long' | 'extreme') => {
    try {
      setSavingRelationshipSettings(true);

      const result = await invoke<RelationshipSettings>('set_relationship_difficulty', {
        userId,
        difficulty,
      });

      setRelationshipSettings(result);
      alert(`✅ Relationship difficulty updated to "${result.description}"`);
    } catch (error) {
      console.error('Failed to update relationship difficulty:', error);
      alert(`❌ Error updating difficulty: ${String(error)}`);
      await loadRelationshipSettings();
    } finally {
      setSavingRelationshipSettings(false);
    }
  };

  if (loadingKeys) {
    return (
      <div className="p-6">
        <GlassCard className="p-6">
          <p className="text-text-secondary">Loading settings...</p>
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="max-w-6xl mx-auto space-y-4">
        {/* Header */}
        <div>
          <h1 className="text-xl font-display text-text-primary mb-1">
            Settings
          </h1>
          <p className="text-sm text-text-secondary">
            Configure API keys and global preferences
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Left Column */}
          <div>
            {/* API Keys Section */}
            <GlassCard className="p-4">
              <button
                onClick={() => togglePanel('apiKeys')}
                className="w-full flex items-center justify-between text-left"
              >
                <h2 className="text-lg font-display text-text-primary">
                  🔑 API Keys
                </h2>
                <span className={`text-text-tertiary transition-transform ${collapsedPanels.apiKeys ? '' : 'rotate-180'}`}>
                  ▼
                </span>
              </button>

              {!collapsedPanels.apiKeys && (
                <>
              <p className="text-xs text-text-tertiary mb-3 mt-2">
                Your API keys are encrypted with your master password and stored securely.
              </p>

              <div className="space-y-3 mb-4">
                {Object.keys(apiKeys).map((provider) => {
                  const status = keyStatuses[provider];
                  const isValidated = status?.validated === true;
                  const isInvalid = status?.validated === false;
                  const isConfigured = status?.configured;

                  return (
                    <div key={provider} className="border-b border-white/10 last:border-0 pb-3 last:pb-0">
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-1.5">
                          <label className="text-sm text-text-primary font-medium">
                            {providerLabels[provider]}
                          </label>
                          {isConfigured && (
                            <span className="text-[10px] bg-accent-success/20 text-accent-success px-1.5 py-0.5 rounded">
                              ✓
                            </span>
                          )}
                          {isValidated && (
                            <span className="text-[10px] bg-accent-success/20 text-accent-success px-1.5 py-0.5 rounded">
                              Valid
                            </span>
                          )}
                          {isInvalid && (
                            <span className="text-[10px] bg-accent-danger/20 text-accent-danger px-1.5 py-0.5 rounded">
                              Invalid
                            </span>
                          )}
                        </div>

                        {isConfigured && (
                          <button
                            onClick={() => handleDeleteKey(provider)}
                            className="text-xs text-accent-danger hover:text-accent-danger/80 transition-colors"
                          >
                            Delete
                          </button>
                        )}
                      </div>

                      <div className="flex gap-1.5">
                        <div className="flex-1 relative">
                          <GlassInput
                            type={showKeys[provider] ? 'text' : 'password'}
                            value={apiKeys[provider]}
                            onChange={(e) => handleKeyChange(provider, e.target.value)}
                            placeholder={providerPlaceholders[provider]}
                            className="w-full text-sm h-8"
                          />
                          <button
                            onClick={() => toggleShowKey(provider)}
                            className="absolute right-2 top-1/2 -translate-y-1/2 text-text-tertiary hover:text-text-primary transition-colors text-xs"
                            title={showKeys[provider] ? 'Hide' : 'Show'}
                          >
                            {showKeys[provider] ? '👁️' : '🔒'}
                          </button>
                        </div>

                        <GlassButton
                          onClick={() => handleValidateKey(provider)}
                          disabled={(!apiKeys[provider] && !isConfigured) || validatingKey === provider}
                          variant="secondary"
                          size="sm"
                          className="px-3 h-8 text-xs"
                        >
                          {validatingKey === provider ? '...' : 'Test'}
                        </GlassButton>

                        <GlassButton
                          onClick={() => handleSaveKey(provider)}
                          disabled={!apiKeys[provider] || savingKey === provider}
                          size="sm"
                          className="px-3 h-8 text-xs"
                        >
                          {savingKey === provider ? '...' : 'Save'}
                        </GlassButton>
                      </div>
                      {status?.validation_message && (
                        <p className={`text-[10px] mt-1 ${isInvalid ? 'text-accent-danger' : 'text-accent-success'}`}>
                          {status.validation_message}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Get API Keys Links - Horizontal */}
              <div className="pt-3 border-t border-white/10">
                <p className="text-[10px] text-text-tertiary mb-2">Get API keys:</p>
                <div className="flex flex-wrap gap-x-3 gap-y-1 text-[10px]">
                  <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-accent-primary hover:underline">
                    OpenAI
                  </a>
                  <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener noreferrer" className="text-accent-primary hover:underline">
                    Anthropic
                  </a>
                  <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" className="text-accent-primary hover:underline">
                    Google
                  </a>
                  <a href="https://platform.deepseek.com/api_keys" target="_blank" rel="noopener noreferrer" className="text-accent-primary hover:underline">
                    DeepSeek
                  </a>
                  <a href="https://www.perplexity.ai/settings/api" target="_blank" rel="noopener noreferrer" className="text-accent-primary hover:underline">
                    Perplexity
                  </a>
                  <a href="https://venice.ai/settings/api" target="_blank" rel="noopener noreferrer" className="text-accent-primary hover:underline">
                    Venice
                  </a>
                  <a href="https://nano-gpt.com/api" target="_blank" rel="noopener noreferrer" className="text-accent-primary hover:underline">
                    NanoGPT
                  </a>
                  <a href="https://app.pinata.cloud/developers/api-keys" target="_blank" rel="noopener noreferrer" className="text-accent-primary hover:underline">
                    Pinata
                  </a>
                </div>
              </div>
                </>
              )}
            </GlassCard>

            {/* Google Cloud TTS Credentials */}
            <GlassCard className="p-4 mt-4">
              <button
                onClick={() => togglePanel('googleTTS')}
                className="w-full flex items-center justify-between text-left"
              >
                <h2 className="text-lg font-display text-text-primary">
                  🎙️ Google Cloud TTS
                </h2>
                <span className={`text-text-tertiary transition-transform ${collapsedPanels.googleTTS ? '' : 'rotate-180'}`}>
                  ▼
                </span>
              </button>

              {!collapsedPanels.googleTTS && (
                <>
              <p className="text-[10px] text-text-tertiary mb-3 mt-2">
                Path to your Google Cloud service account JSON credentials file. Optional - only needed for Google Cloud TTS (30+ voices).
              </p>
              {loadingGoogleTTSPath ? (
                <p className="text-xs text-text-tertiary">Loading...</p>
              ) : (
                <div className="space-y-2">
                  <GlassInput
                    type="text"
                    value={googleTTSPath}
                    onChange={(e) => setGoogleTTSPath(e.target.value)}
                    placeholder="C:/path/to/your-service-account-key.json"
                    className="w-full text-xs"
                  />
                  <div className="flex gap-2">
                    <GlassButton
                      onClick={handleSaveGoogleTTSPath}
                      disabled={savingGoogleTTSPath}
                      size="sm"
                      className="flex-1 text-xs h-7"
                    >
                      {savingGoogleTTSPath ? 'Saving...' : 'Save Path'}
                    </GlassButton>
                    <GlassButton
                      onClick={() => {
                        setGoogleTTSPath('');
                        handleSaveGoogleTTSPath();
                      }}
                      disabled={savingGoogleTTSPath || !googleTTSPath}
                      variant="secondary"
                      size="sm"
                      className="text-xs h-7 px-3"
                    >
                      Clear
                    </GlassButton>
                  </div>
                  <p className="text-[10px] text-text-tertiary">
                    Get your service account JSON from:{' '}
                    <a
                      href="https://console.cloud.google.com/iam-admin/serviceaccounts"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent-primary hover:underline"
                    >
                      Google Cloud Console
                    </a>
                  </p>
                </div>
              )}
                </>
              )}
            </GlassCard>

            {/* Block Preferences */}
            <GlassCard className="p-4 mt-4">
              <button
                onClick={() => togglePanel('blockSettings')}
                className="w-full flex items-center justify-between text-left"
              >
                <h2 className="text-lg font-display text-text-primary">
                  ⚓ Auto-Anchor
                </h2>
                <span className={`text-text-tertiary transition-transform ${collapsedPanels.blockSettings ? '' : 'rotate-180'}`}>
                  ▼
                </span>
              </button>

              {!collapsedPanels.blockSettings && (
                <>
              {loadingPreferences ? (
                <p className="text-xs text-text-tertiary">Loading...</p>
              ) : (
                <div className="space-y-3">
                  {/* Individual Chat Settings */}
                  <div className="border-b border-white/10 pb-3">
                    <h3 className="text-xs font-medium text-text-primary mb-2">
                      Individual Chat
                    </h3>
                    <div className="space-y-2">
                      <label className="flex items-center justify-between text-xs">
                        <span className="text-text-secondary">Auto-anchor</span>
                        <input
                          type="checkbox"
                          checked={blockPreferences.individual_auto_anchor}
                          onChange={(e) => handleToggleChange('individual_auto_anchor', e.target.checked)}
                          disabled={savingPreferences}
                          className="w-4 h-4 rounded bg-surface-secondary border-border-subtle accent-accent-primary"
                        />
                      </label>
                      <label className="flex items-center justify-between text-xs">
                        <span className="text-text-secondary">Anchor every</span>
                        <div className="flex items-center gap-1">
                          <input
                            type="number"
                            min="5"
                            max="50"
                            value={individualThresholdInput}
                            onChange={(e) => setIndividualThresholdInput(e.target.value)}
                            onBlur={(e) => handleThresholdBlur('individual_anchor_threshold', e.target.value)}
                            disabled={savingPreferences}
                            className="w-14 h-6 px-2 text-xs rounded bg-white/90 border border-border-subtle text-gray-900 focus:outline-none focus:border-accent-primary"
                          />
                          <span className="text-text-tertiary text-[10px]">blocks</span>
                        </div>
                      </label>
                    </div>
                  </div>

                  {/* Group Chat Settings */}
                  <div className="border-b border-white/10 pb-3">
                    <h3 className="text-xs font-medium text-text-primary mb-2">
                      Group Chat
                    </h3>
                    <div className="space-y-2">
                      <label className="flex items-center justify-between text-xs">
                        <span className="text-text-secondary">Auto-anchor</span>
                        <input
                          type="checkbox"
                          checked={blockPreferences.group_auto_anchor}
                          onChange={(e) => handleToggleChange('group_auto_anchor', e.target.checked)}
                          disabled={savingPreferences}
                          className="w-4 h-4 rounded bg-surface-secondary border-border-subtle accent-accent-primary"
                        />
                      </label>
                      <label className="flex items-center justify-between text-xs">
                        <span className="text-text-secondary">Anchor every</span>
                        <div className="flex items-center gap-1">
                          <input
                            type="number"
                            min="5"
                            max="50"
                            value={groupThresholdInput}
                            onChange={(e) => setGroupThresholdInput(e.target.value)}
                            onBlur={(e) => handleThresholdBlur('group_anchor_threshold', e.target.value)}
                            disabled={savingPreferences}
                            className="w-14 h-6 px-2 text-xs rounded bg-white/90 border border-border-subtle text-gray-900 focus:outline-none focus:border-accent-primary"
                          />
                          <span className="text-text-tertiary text-[10px]">blocks</span>
                        </div>
                      </label>
                    </div>
                  </div>

                  {/* IPFS Sync Settings */}
                  <div>
                    <h3 className="text-xs font-medium text-text-primary mb-2">
                      IPFS Sync
                    </h3>
                    <div className="space-y-2">
                      <label className="flex items-center justify-between text-xs">
                        <span className="text-text-secondary">Sync to IPFS after auto-anchor</span>
                        <input
                          type="checkbox"
                          checked={blockPreferences.auto_sync_ipfs_on_anchor}
                          onChange={(e) => handleToggleChange('auto_sync_ipfs_on_anchor', e.target.checked)}
                          disabled={savingPreferences}
                          className="w-4 h-4 rounded bg-surface-secondary border-border-subtle accent-accent-primary"
                        />
                      </label>
                      <p className="text-[10px] text-text-tertiary">
                        Automatically upload .qube package to IPFS after each auto-anchor
                      </p>
                    </div>
                  </div>
                </div>
              )}
                </>
              )}
            </GlassCard>

            {/* Block Recall Settings */}
            <GlassCard className="p-4 mt-4">
              <button
                onClick={() => togglePanel('blockRecall')}
                className="w-full flex items-center justify-between text-left"
              >
                <h2 className="text-lg font-display text-text-primary">
                  🔮 Block Recall
                </h2>
                <span className={`text-text-tertiary transition-transform ${collapsedPanels.blockRecall ? '' : 'rotate-180'}`}>
                  ▼
                </span>
              </button>

              {!collapsedPanels.blockRecall && (
                <>
              <p className="text-[10px] text-text-tertiary mb-3 mt-2">
                Configure how memories are recalled and injected into conversations.
              </p>

              {loadingMemoryConfig ? (
                <p className="text-xs text-text-tertiary">Loading...</p>
              ) : (
                <div className="space-y-3">
                  {/* Basic Settings */}
                  <div className="space-y-2">
                    {/* Recall Threshold */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <label className="text-xs text-text-secondary">Recall Threshold</label>
                        <span className="text-xs text-text-primary font-mono">{localMemoryConfig.recall_threshold.toFixed(1)}</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        step="1"
                        value={localMemoryConfig.recall_threshold}
                        onChange={(e) => handleMemoryConfigSliderChange({ recall_threshold: parseFloat(e.target.value) })}
                        onPointerUp={handleMemoryConfigSliderRelease}
                        onTouchEnd={handleMemoryConfigSliderRelease}
                        className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-primary"
                      />
                      <p className="text-[9px] text-text-tertiary">Minimum relevance score (0-100) to recall a memory</p>
                    </div>

                    {/* Max Recalls */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <label className="text-xs text-text-secondary">Max Recalls</label>
                        <span className="text-xs text-text-primary font-mono">{localMemoryConfig.max_recalls}</span>
                      </div>
                      <input
                        type="range"
                        min="1"
                        max="20"
                        step="1"
                        value={localMemoryConfig.max_recalls}
                        onChange={(e) => handleMemoryConfigSliderChange({ max_recalls: parseInt(e.target.value) })}
                        onPointerUp={handleMemoryConfigSliderRelease}
                        onTouchEnd={handleMemoryConfigSliderRelease}
                        className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-primary"
                      />
                      <p className="text-[9px] text-text-tertiary">Maximum memories to inject per query</p>
                    </div>

                    {/* Decay Rate */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <label className="text-xs text-text-secondary">Temporal Decay Rate</label>
                        <span className="text-xs text-text-primary font-mono">{localMemoryConfig.decay_rate.toFixed(2)}</span>
                      </div>
                      <input
                        type="range"
                        min="0.01"
                        max="1"
                        step="0.01"
                        value={localMemoryConfig.decay_rate}
                        onChange={(e) => handleMemoryConfigSliderChange({ decay_rate: parseFloat(e.target.value) })}
                        onPointerUp={handleMemoryConfigSliderRelease}
                        onTouchEnd={handleMemoryConfigSliderRelease}
                        className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-primary"
                      />
                      <p className="text-[9px] text-text-tertiary">
                        {localMemoryConfig.decay_rate <= 0.2 ? 'Slow decay - older memories stay relevant longer' :
                         localMemoryConfig.decay_rate >= 0.8 ? 'Fast decay - strongly favors recent memories' :
                         'Moderate decay - balanced recency preference'}
                      </p>
                    </div>
                  </div>

                  {/* Advanced Settings Toggle */}
                  <button
                    onClick={() => setShowAdvancedRecall(!showAdvancedRecall)}
                    className="flex items-center gap-2 text-xs text-accent-primary hover:text-accent-primary/80 transition-colors"
                  >
                    <span className={`transform transition-transform ${showAdvancedRecall ? 'rotate-90' : ''}`}>▶</span>
                    Advanced Recall Settings
                  </button>

                  {/* Advanced Settings (Collapsible) */}
                  {showAdvancedRecall && (
                    <div className="space-y-2 pl-4 border-l-2 border-white/10">
                      <p className="text-[9px] text-text-tertiary mb-2">
                        Scoring weights determine how different factors contribute to relevance. Should sum to ~1.0.
                      </p>

                      {/* Semantic Weight */}
                      <div className="space-y-1">
                        <div className="flex items-center justify-between">
                          <label className="text-[10px] text-text-secondary">Semantic Weight</label>
                          <span className="text-[10px] text-text-primary font-mono">{localMemoryConfig.semantic_weight.toFixed(2)}</span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.05"
                          value={localMemoryConfig.semantic_weight}
                          onChange={(e) => handleMemoryConfigSliderChange({ semantic_weight: parseFloat(e.target.value) })}
                          onPointerUp={handleMemoryConfigSliderRelease}
                          onTouchEnd={handleMemoryConfigSliderRelease}
                          className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-primary"
                        />
                        <p className="text-[8px] text-text-tertiary">Meaning/context similarity via embeddings</p>
                      </div>

                      {/* Keyword Weight */}
                      <div className="space-y-1">
                        <div className="flex items-center justify-between">
                          <label className="text-[10px] text-text-secondary">Keyword Weight</label>
                          <span className="text-[10px] text-text-primary font-mono">{localMemoryConfig.keyword_weight.toFixed(2)}</span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.05"
                          value={localMemoryConfig.keyword_weight}
                          onChange={(e) => handleMemoryConfigSliderChange({ keyword_weight: parseFloat(e.target.value) })}
                          onPointerUp={handleMemoryConfigSliderRelease}
                          onTouchEnd={handleMemoryConfigSliderRelease}
                          className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-primary"
                        />
                        <p className="text-[8px] text-text-tertiary">Exact word/phrase matches</p>
                      </div>

                      {/* Temporal Weight */}
                      <div className="space-y-1">
                        <div className="flex items-center justify-between">
                          <label className="text-[10px] text-text-secondary">Temporal Weight</label>
                          <span className="text-[10px] text-text-primary font-mono">{localMemoryConfig.temporal_weight.toFixed(2)}</span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.05"
                          value={localMemoryConfig.temporal_weight}
                          onChange={(e) => handleMemoryConfigSliderChange({ temporal_weight: parseFloat(e.target.value) })}
                          onPointerUp={handleMemoryConfigSliderRelease}
                          onTouchEnd={handleMemoryConfigSliderRelease}
                          className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-primary"
                        />
                        <p className="text-[8px] text-text-tertiary">Recency boost for newer memories</p>
                      </div>

                      {/* Relationship Weight */}
                      <div className="space-y-1">
                        <div className="flex items-center justify-between">
                          <label className="text-[10px] text-text-secondary">Relationship Weight</label>
                          <span className="text-[10px] text-text-primary font-mono">{localMemoryConfig.relationship_weight.toFixed(2)}</span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.05"
                          value={localMemoryConfig.relationship_weight}
                          onChange={(e) => handleMemoryConfigSliderChange({ relationship_weight: parseFloat(e.target.value) })}
                          onPointerUp={handleMemoryConfigSliderRelease}
                          onTouchEnd={handleMemoryConfigSliderRelease}
                          className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-primary"
                        />
                        <p className="text-[8px] text-text-tertiary">Boost for memories involving close relationships</p>
                      </div>

                      {/* Weight Sum Indicator */}
                      <div className="mt-2 pt-2 border-t border-white/10">
                        <div className="flex items-center justify-between">
                          <span className="text-[9px] text-text-tertiary">Total Weight Sum:</span>
                          <span className={`text-[10px] font-mono ${
                            Math.abs((localMemoryConfig.semantic_weight + localMemoryConfig.keyword_weight + localMemoryConfig.temporal_weight + localMemoryConfig.relationship_weight) - 1) < 0.05
                              ? 'text-accent-success'
                              : 'text-accent-warning'
                          }`}>
                            {(localMemoryConfig.semantic_weight + localMemoryConfig.keyword_weight + localMemoryConfig.temporal_weight + localMemoryConfig.relationship_weight).toFixed(2)}
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
                </>
              )}
            </GlassCard>

            {/* Custom Voices */}
            <GlassCard className="p-4 mt-4">
              <button
                onClick={() => togglePanel('voiceSettings')}
                className="w-full flex items-center justify-between text-left"
              >
                <h2 className="text-lg font-display text-text-primary">
                  🎤 Custom Voices
                </h2>
                <span className={`text-text-tertiary transition-transform ${collapsedPanels.voiceSettings ? '' : 'rotate-180'}`}>
                  ▼
                </span>
              </button>

              {!collapsedPanels.voiceSettings && (
                <>
                  <p className="text-[10px] text-text-tertiary mb-3 mt-2">
                    Create unique voices for your Qubes using AI voice design, cloning, or presets.
                  </p>

                  <VoiceSettingsPanel
                    selectedQubeId={selectedQubeIdForSettings}
                    selectedQubeName={availableQubes.find(q => q.qube_id === selectedQubeIdForSettings)?.name}
                  />
                </>
              )}
            </GlassCard>
          </div>

          {/* Right Column */}
          <div>
            {/* Relationship Difficulty */}
            <GlassCard className="p-4">
              <button
                onClick={() => togglePanel('relationshipDifficulty')}
                className="w-full flex items-center justify-between text-left"
              >
                <h2 className="text-lg font-display text-text-primary">
                  💞 Relationship Difficulty
                </h2>
                <span className={`text-text-tertiary transition-transform ${collapsedPanels.relationshipDifficulty ? '' : 'rotate-180'}`}>
                  ▼
                </span>
              </button>

              {!collapsedPanels.relationshipDifficulty && (
                <>
              <p className="text-[10px] text-text-tertiary mb-3 mt-2">
                Global setting that affects all qubes equally. Determines how quickly relationships build.
              </p>

              {loadingRelationshipSettings ? (
                <p className="text-xs text-text-tertiary">Loading...</p>
              ) : (
                <div className="space-y-3">
                  {/* Current Setting */}
                  <div className="bg-white/5 rounded p-2 border border-white/10">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-text-primary">Current:</span>
                      <span className="text-xs text-accent-primary font-semibold uppercase">
                        {relationshipSettings.difficulty}
                      </span>
                    </div>
                    <p className="text-[10px] text-text-secondary italic">
                      {relationshipSettings.description}
                    </p>
                  </div>

                  {/* Difficulty Buttons */}
                  <div className="grid grid-cols-2 gap-2">
                    {(['quick', 'normal', 'long', 'extreme'] as const).map((difficulty) => (
                      <button
                        key={difficulty}
                        onClick={() => handleDifficultyChange(difficulty)}
                        disabled={savingRelationshipSettings || relationshipSettings.difficulty === difficulty}
                        className={`
                          px-3 py-2 rounded text-xs font-medium transition-all
                          ${relationshipSettings.difficulty === difficulty
                            ? 'bg-accent-primary/20 text-accent-primary border-2 border-accent-primary/40'
                            : 'bg-white/5 text-text-secondary border border-white/10 hover:bg-white/10 hover:text-text-primary'
                          }
                          disabled:opacity-50 disabled:cursor-not-allowed
                        `}
                      >
                        {difficulty === 'quick' && '⚡ Quick'}
                        {difficulty === 'normal' && '⚖️ Normal'}
                        {difficulty === 'long' && '🏔️ Long'}
                        {difficulty === 'extreme' && '🔥 Extreme'}
                      </button>
                    ))}
                  </div>

                  {/* Current Preset Stats (if available) */}
                  {difficultyPresets[relationshipSettings.difficulty] && (
                    <div className="border-t border-white/10 pt-3">
                      <h3 className="text-[10px] font-medium text-text-primary mb-2">
                        Required Interactions:
                      </h3>
                      <div className="grid grid-cols-2 gap-1.5 text-[10px]">
                        <div className="flex justify-between">
                          <span className="text-text-tertiary">Acquaintance:</span>
                          <span className="text-text-primary font-mono">
                            {difficultyPresets[relationshipSettings.difficulty].min_interactions.acquaintance}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-text-tertiary">Friend:</span>
                          <span className="text-text-primary font-mono">
                            {difficultyPresets[relationshipSettings.difficulty].min_interactions.friend}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-text-tertiary">Close Friend:</span>
                          <span className="text-text-primary font-mono">
                            {difficultyPresets[relationshipSettings.difficulty].min_interactions.close_friend}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-text-tertiary">Best Friend:</span>
                          <span className="text-text-primary font-mono">
                            {difficultyPresets[relationshipSettings.difficulty].min_interactions.best_friend}
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
                </>
              )}
            </GlassCard>

            {/* Trust Personality */}
            <GlassCard className="p-4 mt-4">
              <button
                onClick={() => togglePanel('trustPersonality')}
                className="w-full flex items-center justify-between text-left"
              >
                <h2 className="text-lg font-display text-text-primary">
                  🎭 Trust Personality
                </h2>
                <span className={`text-text-tertiary transition-transform ${collapsedPanels.trustPersonality ? '' : 'rotate-180'}`}>
                  ▼
                </span>
              </button>

              {!collapsedPanels.trustPersonality && (
                <>
              <p className="text-[10px] text-text-tertiary mb-3 mt-2">
                Configure how each Qube evaluates trust in relationships.
              </p>

              {/* Qube Selector */}
                <div className="mb-3">
                  <label className="text-[10px] text-text-secondary mb-1 block">Select Qube:</label>
                  <select
                    value={selectedQubeForTrust}
                    onChange={(e) => setSelectedQubeForTrust(e.target.value)}
                    disabled={loadingTrustPersonality}
                    className="w-full h-7 px-2 text-xs rounded bg-bg-secondary border border-border-subtle text-text-primary focus:outline-none focus:border-accent-primary disabled:opacity-50"
                  >
                    {availableQubes.map((q) => (
                      <option key={q.qube_id} value={q.qube_id}>
                        {q.name} ({q.qube_id})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Trust Personality Buttons */}
                {loadingTrustPersonality ? (
                  <p className="text-xs text-text-tertiary">Loading...</p>
                ) : (
                  <div className="grid grid-cols-2 gap-2">
                    {(['cautious', 'balanced', 'social', 'analytical'] as const).map((personality) => {
                      const descriptions = {
                        cautious: 'Trust slowly, prioritize reliability & honesty',
                        balanced: 'Equal weight to all trust components',
                        social: 'Value communication & responsiveness',
                        analytical: 'Prioritize expertise & competence'
                      };
                      const icons = {
                        cautious: '🛡️',
                        balanced: '⚖️',
                        social: '💬',
                        analytical: '🔬'
                      };

                      const isSelected = trustPersonality === personality;

                      return (
                        <button
                          key={personality}
                          onClick={() => handleTrustPersonalityChange(personality)}
                          disabled={savingTrustPersonality}
                          className={`
                            px-3 py-2 rounded text-xs transition-all
                            ${isSelected
                              ? 'bg-accent-primary/20 border-2 border-accent-primary/40 text-accent-primary font-semibold'
                              : 'bg-white/5 border border-white/10 text-text-secondary hover:bg-white/10 hover:text-text-primary'
                            }
                            disabled:opacity-50 disabled:cursor-not-allowed
                          `}
                          title={descriptions[personality]}
                        >
                          <div className="flex items-center justify-center gap-1.5">
                            <span>{icons[personality]}</span>
                            <span className="capitalize">{personality}</span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}

                {/* Description of Selected Personality */}
                <div className="mt-3 bg-white/5 rounded p-2 border border-white/10">
                  <p className="text-[10px] text-text-secondary italic">
                    {trustPersonality === 'cautious' && 'This Qube will build trust slowly, emphasizing reliability and honesty over speed.'}
                    {trustPersonality === 'balanced' && 'This Qube gives equal weight to all trust components for balanced relationship growth.'}
                    {trustPersonality === 'social' && 'This Qube values good communication and quick responses in building trust.'}
                    {trustPersonality === 'analytical' && 'This Qube prioritizes demonstrated expertise and competence when evaluating trust.'}
                  </p>
                </div>
                </>
              )}
            </GlassCard>

            {/* Decision Intelligence */}
            <GlassCard className="p-4 mt-4">
              <button
                onClick={() => togglePanel('decisionIntelligence')}
                className="w-full flex items-center justify-between text-left"
              >
                <h2 className="text-lg font-display text-text-primary">
                  🧠 Decision Intelligence
                </h2>
                <span className={`text-text-tertiary transition-transform ${collapsedPanels.decisionIntelligence ? '' : 'rotate-180'}`}>
                  ▼
                </span>
              </button>

              {!collapsedPanels.decisionIntelligence && (
                <>
              <p className="text-[10px] text-text-tertiary mb-3 mt-2">
                Configure how Qubes use relationship and self-evaluation metrics to make better decisions.
              </p>

              {loadingDecisionConfig ? (
                  <p className="text-xs text-text-tertiary">Loading...</p>
                ) : (
                  <div className="space-y-4">
                    {/* Thresholds Section */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-medium text-text-primary">Decision Thresholds (0-100)</h4>
                        {decisionConfig.auto_thresholds && (
                          <span className="text-[9px] text-accent-primary bg-accent-primary/10 px-2 py-0.5 rounded">
                            AUTO MODE
                          </span>
                        )}
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        <div className="space-y-1">
                          <label className="text-[10px] text-text-secondary">Trust: {decisionConfig.trust_threshold}</label>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            value={decisionConfig.trust_threshold}
                            onChange={(e) => handleDecisionConfigChange({ trust_threshold: parseInt(e.target.value) })}
                            disabled={savingDecisionConfig || decisionConfig.auto_thresholds}
                            className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-primary disabled:opacity-50 disabled:cursor-not-allowed"
                          />
                        </div>

                        <div className="space-y-1">
                          <label className="text-[10px] text-text-secondary">Expertise: {decisionConfig.expertise_threshold}</label>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            value={decisionConfig.expertise_threshold}
                            onChange={(e) => handleDecisionConfigChange({ expertise_threshold: parseInt(e.target.value) })}
                            disabled={savingDecisionConfig || decisionConfig.auto_thresholds}
                            className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-primary disabled:opacity-50 disabled:cursor-not-allowed"
                          />
                        </div>

                        <div className="space-y-1">
                          <label className="text-[10px] text-text-secondary">Collaboration: {decisionConfig.collaboration_threshold}</label>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            value={decisionConfig.collaboration_threshold}
                            onChange={(e) => handleDecisionConfigChange({ collaboration_threshold: parseInt(e.target.value) })}
                            disabled={savingDecisionConfig || decisionConfig.auto_thresholds}
                            className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-primary disabled:opacity-50 disabled:cursor-not-allowed"
                          />
                        </div>

                        <div className="space-y-1">
                          <label className="text-[10px] text-text-secondary">Confidence: {decisionConfig.confidence_threshold}</label>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            value={decisionConfig.confidence_threshold}
                            onChange={(e) => handleDecisionConfigChange({ confidence_threshold: parseInt(e.target.value) })}
                            disabled={savingDecisionConfig || decisionConfig.auto_thresholds}
                            className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-primary disabled:opacity-50 disabled:cursor-not-allowed"
                          />
                        </div>
                      </div>

                      {decisionConfig.auto_thresholds && (
                        <p className="text-[9px] text-text-tertiary italic">
                          Thresholds are auto-calculated from self-evaluation metrics and update with each snapshot
                        </p>
                      )}
                    </div>

                    {/* Influence Levels Section */}
                    <div className="space-y-2 border-t border-white/10 pt-3">
                      <h4 className="text-xs font-medium text-text-primary">Influence Levels (0-100%)</h4>

                      <div className="grid grid-cols-2 gap-2">
                        <div className="space-y-1">
                          <label className="text-[10px] text-text-secondary">Metric Influence: {decisionConfig.metric_influence}%</label>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            value={decisionConfig.metric_influence}
                            onChange={(e) => handleDecisionConfigChange({ metric_influence: parseInt(e.target.value) })}
                            disabled={savingDecisionConfig}
                            className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-primary"
                          />
                        </div>

                        <div className="space-y-1">
                          <label className="text-[10px] text-text-secondary">Validation Strictness: {decisionConfig.validation_strictness}%</label>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            value={decisionConfig.validation_strictness}
                            onChange={(e) => handleDecisionConfigChange({ validation_strictness: parseInt(e.target.value) })}
                            disabled={savingDecisionConfig}
                            className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-primary"
                          />
                          <p className="text-[9px] text-text-tertiary italic">
                            {decisionConfig.validation_strictness >= 80 ? 'Hard: Can block actions' :
                             decisionConfig.validation_strictness >= 40 ? 'Medium: Warnings + confidence reduction' :
                             'Soft: Warnings only'}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Negative Metric Tolerances Section */}
                    <div className="space-y-2 border-t border-white/10 pt-3">
                      <h4 className="text-xs font-medium text-text-primary">Negative Metric Tolerances (0-100)</h4>

                      <div className="grid grid-cols-3 gap-2">
                        <div className="space-y-1">
                          <label className="text-[10px] text-text-secondary">Max Antagonism: {decisionConfig.max_antagonism}</label>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            value={decisionConfig.max_antagonism}
                            onChange={(e) => handleDecisionConfigChange({ max_antagonism: parseInt(e.target.value) })}
                            disabled={savingDecisionConfig}
                            className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-primary"
                          />
                        </div>

                        <div className="space-y-1">
                          <label className="text-[10px] text-text-secondary">Max Distrust: {decisionConfig.max_distrust}</label>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            value={decisionConfig.max_distrust}
                            onChange={(e) => handleDecisionConfigChange({ max_distrust: parseInt(e.target.value) })}
                            disabled={savingDecisionConfig}
                            className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-primary"
                          />
                        </div>

                        <div className="space-y-1">
                          <label className="text-[10px] text-text-secondary">Max Betrayal: {decisionConfig.max_betrayal}</label>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            value={decisionConfig.max_betrayal}
                            onChange={(e) => handleDecisionConfigChange({ max_betrayal: parseInt(e.target.value) })}
                            disabled={savingDecisionConfig}
                            className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-accent-primary"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Feature Toggles Section */}
                    <div className="space-y-2 border-t border-white/10 pt-3">
                      <h4 className="text-xs font-medium text-text-primary">Feature Toggles</h4>

                      <div className="space-y-1.5">
                        <label className="flex items-center space-x-2 text-[10px] text-text-secondary cursor-pointer">
                          <input
                            type="checkbox"
                            checked={decisionConfig.enable_validation_layer}
                            onChange={(e) => handleDecisionConfigChange({ enable_validation_layer: e.target.checked })}
                            disabled={savingDecisionConfig}
                            className="rounded border-white/20 bg-white/5 text-accent-primary focus:ring-accent-primary focus:ring-offset-0"
                          />
                          <span>Enable Validation Layer (pre-flight checks)</span>
                        </label>

                        <label className="flex items-center space-x-2 text-[10px] text-text-secondary cursor-pointer">
                          <input
                            type="checkbox"
                            checked={decisionConfig.enable_metric_tools}
                            onChange={(e) => handleDecisionConfigChange({ enable_metric_tools: e.target.checked })}
                            disabled={savingDecisionConfig}
                            className="rounded border-white/20 bg-white/5 text-accent-primary focus:ring-accent-primary focus:ring-offset-0"
                          />
                          <span>Enable Metric Tools (decision context, capability check)</span>
                        </label>

                        <label className="flex items-center space-x-2 text-[10px] text-text-secondary cursor-pointer">
                          <input
                            type="checkbox"
                            checked={decisionConfig.enable_auto_temperature}
                            onChange={(e) => handleDecisionConfigChange({ enable_auto_temperature: e.target.checked })}
                            disabled={savingDecisionConfig}
                            className="rounded border-white/20 bg-white/5 text-accent-primary focus:ring-accent-primary focus:ring-offset-0"
                          />
                          <span>Enable Auto Temperature Adjustment</span>
                        </label>

                        <label className="flex items-center space-x-2 text-[10px] text-text-secondary cursor-pointer">
                          <input
                            type="checkbox"
                            checked={decisionConfig.auto_thresholds}
                            onChange={(e) => handleDecisionConfigChange({ auto_thresholds: e.target.checked })}
                            disabled={savingDecisionConfig}
                            className="rounded border-white/20 bg-white/5 text-accent-primary focus:ring-accent-primary focus:ring-offset-0"
                          />
                          <span>Auto-Adjust Thresholds (from self-evaluation)</span>
                        </label>
                      </div>
                    </div>
                  </div>
                )}
                </>
              )}
            </GlassCard>

            {/* Security Settings */}
            <GlassCard className="p-4 mt-4">
              <button
                onClick={() => togglePanel('security')}
                className="w-full flex items-center justify-between text-left"
              >
                <h2 className="text-lg font-display text-text-primary">
                  🔐 Security
                </h2>
                <span className={`text-text-tertiary transition-transform ${collapsedPanels.security ? '' : 'rotate-180'}`}>
                  ▼
                </span>
              </button>

              {!collapsedPanels.security && (
                <>
              <p className="text-[10px] text-text-tertiary mb-3 mt-2">
                Configure security features to protect your Qubes and data.
              </p>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-medium text-text-primary">Auto-Lock</h3>
                    <p className="text-[10px] text-text-tertiary">
                      Lock the app after a period of inactivity
                    </p>
                  </div>
                  <button
                    onClick={() => setAutoLockSettings(!autoLockEnabled, autoLockTimeout)}
                    className={`w-12 h-6 rounded-full transition-colors duration-200 relative ${
                      autoLockEnabled ? 'bg-accent-primary' : 'bg-white/20'
                    }`}
                  >
                    <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform duration-200 ${
                      autoLockEnabled ? 'translate-x-7' : 'translate-x-1'
                    }`} />
                  </button>
                </div>

                {autoLockEnabled && (
                  <div className="pl-4 border-l-2 border-accent-primary/30">
                    <label className="text-xs text-text-secondary block mb-2">
                      Lock after inactivity:
                    </label>
                    <div className="grid grid-cols-4 gap-2">
                      {[5, 10, 15, 30].map((minutes) => (
                        <button
                          key={minutes}
                          onClick={() => setAutoLockSettings(autoLockEnabled, minutes)}
                          className={`px-3 py-2 rounded text-xs font-medium transition-all ${
                            autoLockTimeout === minutes
                              ? 'bg-accent-primary/20 text-accent-primary border-2 border-accent-primary/40'
                              : 'bg-white/5 text-text-secondary border border-white/10 hover:bg-white/10'
                          }`}
                        >
                          {minutes} min
                        </button>
                      ))}
                    </div>
                    <p className="text-[9px] text-text-tertiary mt-2 italic">
                      You'll need to enter your password to unlock
                    </p>
                  </div>
                )}
              </div>
                </>
              )}
            </GlassCard>

            {/* Software Updates Section */}
            <GlassCard className="p-4 mt-4">
              <button
                onClick={() => togglePanel('softwareUpdates')}
                className="w-full flex items-center justify-between text-left"
              >
                <h2 className="text-lg font-display text-text-primary">
                  🔄 Software Updates
                </h2>
                <span className={`text-text-tertiary transition-transform ${collapsedPanels.softwareUpdates ? '' : 'rotate-180'}`}>
                  ▼
                </span>
              </button>

              {!collapsedPanels.softwareUpdates && (
                <>
              <p className="text-[10px] text-text-tertiary mb-3 mt-2">
                Keep Qubes up to date with the latest features and security fixes.
              </p>

              <div className="space-y-3">
                {/* Update Available Banner */}
                {updateAvailable && updateStatus && (
                  <div className="bg-accent-primary/10 border border-accent-primary/30 rounded-lg p-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-accent-primary">
                          Update Available!
                        </p>
                        <p className="text-[10px] text-text-secondary">
                          Version {updateStatus.newVersion} is ready to install
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <GlassButton
                          onClick={dismissUpdate}
                          variant="secondary"
                          size="sm"
                          className="text-xs h-7 px-3"
                        >
                          Later
                        </GlassButton>
                        <GlassButton
                          onClick={installUpdate}
                          disabled={isDownloading}
                          size="sm"
                          className="text-xs h-7 px-3"
                        >
                          {isDownloading ? 'Installing...' : 'Install Now'}
                        </GlassButton>
                      </div>
                    </div>
                    {isDownloading && downloadProgress && (
                      <div className="mt-2">
                        <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-accent-primary transition-all duration-300"
                            style={{
                              width: `${(downloadProgress.downloaded / downloadProgress.total) * 100}%`
                            }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Current Version & Check Button */}
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-text-secondary">Current Version</p>
                    <p className="text-sm font-mono text-text-primary">
                      {updateStatus?.currentVersion || 'Unknown'}
                    </p>
                  </div>
                  <GlassButton
                    onClick={checkForUpdates}
                    disabled={isChecking}
                    variant="secondary"
                    size="sm"
                    className="text-xs h-8 px-4"
                  >
                    {isChecking ? 'Checking...' : 'Check for Updates'}
                  </GlassButton>
                </div>

                {/* Error Display */}
                {updateError && (
                  <p className="text-[10px] text-accent-danger">
                    Error: {updateError}
                  </p>
                )}

                {/* No Update Available Message */}
                {updateStatus && !updateStatus.available && !updateError && !isChecking && (
                  <p className="text-[10px] text-accent-success">
                    ✓ You're running the latest version
                  </p>
                )}
              </div>
                </>
              )}
            </GlassCard>
          </div>
        </div>
      </div>
    </div>
  );
};
