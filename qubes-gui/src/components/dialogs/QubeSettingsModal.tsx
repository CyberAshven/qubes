import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { GlassCard, GlassButton } from '../glass';
import { useModels } from '../../hooks/useModels';
import { useAuth } from '../../hooks/useAuth';

interface QubeSettingsModalProps {
  isOpen: boolean;
  qubeId: string;
  qubeName: string;
  currentModel: string;
  modelLocked: boolean;
  lockedToModel: string | null;
  revolverMode: boolean;
  revolverProviders: string[];
  revolverModels: string[];  // Individual model IDs for revolver mode
  freeMode: boolean;  // Default autonomous mode
  freeModeModels: string[];  // Individual model IDs for free mode
  onClose: () => void;
  onUpdate: (updates: {
    modelLocked: boolean;
    lockedToModel: string | null;
    revolverMode: boolean;
    revolverProviders: string[];
    revolverModels: string[];
    freeMode: boolean;
    freeModeModels: string[];
  }) => void;
}

// Provider display names
const PROVIDER_LABELS: Record<string, string> = {
  venice: 'Venice AI',
  google: 'Google (Gemini)',
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  openrouter: 'OpenRouter',
  deepseek: 'DeepSeek',
  xai: 'xAI (Grok)',
  perplexity: 'Perplexity',
  ollama: 'Ollama (Local)',
  nanogpt: 'NanoGPT',
};

// Non-AI providers to filter out
const NON_AI_PROVIDERS = ['pinata_jwt', 'pinata', 'huggingface_token'];

export const QubeSettingsModal: React.FC<QubeSettingsModalProps> = ({
  isOpen,
  qubeId,
  qubeName,
  currentModel,
  modelLocked: initialModelLocked,
  lockedToModel: initialLockedToModel,
  revolverMode: initialRevolverMode,
  revolverProviders: initialRevolverProviders,
  revolverModels: initialRevolverModels,
  freeMode: initialFreeMode,
  freeModeModels: initialFreeModeModels,
  onClose,
  onUpdate,
}) => {
  const { userId, password: masterPassword } = useAuth();
  const { providers, models, isLoaded, fetchModels, formatModelName } = useModels();

  // Local state - only one of the three modes can be active
  // Default to modelLocked if none of the modes is explicitly on
  const [modelLocked, setModelLocked] = useState(initialModelLocked || (!initialRevolverMode && !initialFreeMode));
  const [revolverMode, setRevolverMode] = useState(initialRevolverMode);
  const [freeMode, setFreeMode] = useState(initialFreeMode);
  // Track selected models for revolver mode (stored as "provider:model" strings)
  const [selectedRevolverModels, setSelectedRevolverModels] = useState<Set<string>>(new Set());
  // Track selected models for free mode (stored as "provider:model" strings)
  const [selectedFreeModeModels, setSelectedFreeModeModels] = useState<Set<string>>(new Set());
  const [configuredProviders, setConfiguredProviders] = useState<string[]>([]);
  const [expandedProviders, setExpandedProviders] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [loadingProviders, setLoadingProviders] = useState(false);

  // Sync state when props change
  useEffect(() => {
    setRevolverMode(initialRevolverMode);
    setFreeMode(initialFreeMode);
    // Default to modelLocked if none of the modes is explicitly on
    setModelLocked(initialModelLocked || (!initialRevolverMode && !initialFreeMode));
  }, [initialModelLocked, initialRevolverMode, initialFreeMode, isOpen]);

  // Load models and configured providers on mount
  useEffect(() => {
    if (isOpen) {
      fetchModels();
      loadConfiguredProviders();
    }
  }, [isOpen, fetchModels]);

  // Initialize selected models for revolver mode
  useEffect(() => {
    if (isLoaded && configuredProviders.length > 0) {
      // If no models are selected (empty = all), select all available models
      if (initialRevolverModels.length === 0) {
        const allModels = new Set<string>();
        getAvailableProviders().forEach(provider => {
          const providerModels = models[provider] || [];
          providerModels.forEach(m => allModels.add(`${provider}:${m.value}`));
        });
        setSelectedRevolverModels(allModels);
      } else {
        // Select only the specific models that were saved
        const selected = new Set<string>();
        getAvailableProviders().forEach(provider => {
          const providerModels = models[provider] || [];
          providerModels.forEach(m => {
            if (initialRevolverModels.includes(m.value)) {
              selected.add(`${provider}:${m.value}`);
            }
          });
        });
        setSelectedRevolverModels(selected);
      }
    }
  }, [isLoaded, configuredProviders, initialRevolverModels, models]);

  // Initialize selected models for free mode
  useEffect(() => {
    if (isLoaded && configuredProviders.length > 0) {
      // If no models are selected (empty = all), select all available models
      if (initialFreeModeModels.length === 0) {
        const allModels = new Set<string>();
        getAvailableProviders().forEach(provider => {
          const providerModels = models[provider] || [];
          providerModels.forEach(m => allModels.add(`${provider}:${m.value}`));
        });
        setSelectedFreeModeModels(allModels);
      } else {
        // Select only the specific models that were saved
        const selected = new Set<string>();
        getAvailableProviders().forEach(provider => {
          const providerModels = models[provider] || [];
          providerModels.forEach(m => {
            if (initialFreeModeModels.includes(m.value)) {
              selected.add(`${provider}:${m.value}`);
            }
          });
        });
        setSelectedFreeModeModels(selected);
      }
    }
  }, [isLoaded, configuredProviders, initialFreeModeModels, models]);

  const loadConfiguredProviders = async () => {
    if (!userId || !masterPassword) return;
    setLoadingProviders(true);
    try {
      const result = await invoke<{ providers: string[] }>('get_configured_api_keys', {
        userId,
        password: masterPassword,
      });
      // Filter out non-AI providers
      const aiProviders = result.providers.filter(p => !NON_AI_PROVIDERS.includes(p.toLowerCase()));
      setConfiguredProviders(aiProviders);
    } catch (error) {
      console.error('Failed to load configured providers:', error);
    } finally {
      setLoadingProviders(false);
    }
  };

  // Get providers that are configured AND have models in the registry
  const getAvailableProviders = (): string[] => {
    const available: string[] = [];
    configuredProviders.forEach(provider => {
      if (models[provider] && models[provider].length > 0) {
        available.push(provider);
      }
    });
    // Always check for Ollama if it has models (local, no API key needed)
    if (models['ollama'] && models['ollama'].length > 0) {
      if (!available.includes('ollama')) {
        available.push('ollama');
      }
    }
    return available;
  };

  if (!isOpen) return null;

  // Toggle functions for revolver mode
  const toggleRevolverProvider = (provider: string) => {
    const providerModels = models[provider] || [];
    const providerModelKeys = providerModels.map(m => `${provider}:${m.value}`);

    const allSelected = providerModelKeys.every(key => selectedRevolverModels.has(key));

    const newSelected = new Set(selectedRevolverModels);
    if (allSelected) {
      providerModelKeys.forEach(key => newSelected.delete(key));
    } else {
      providerModelKeys.forEach(key => newSelected.add(key));
    }
    setSelectedRevolverModels(newSelected);
  };

  const toggleRevolverModel = (provider: string, modelValue: string) => {
    const key = `${provider}:${modelValue}`;
    const newSelected = new Set(selectedRevolverModels);
    if (newSelected.has(key)) {
      newSelected.delete(key);
    } else {
      newSelected.add(key);
    }
    setSelectedRevolverModels(newSelected);
  };

  // Toggle functions for free mode
  const toggleFreeModeProvider = (provider: string) => {
    const providerModels = models[provider] || [];
    const providerModelKeys = providerModels.map(m => `${provider}:${m.value}`);

    const allSelected = providerModelKeys.every(key => selectedFreeModeModels.has(key));

    const newSelected = new Set(selectedFreeModeModels);
    if (allSelected) {
      providerModelKeys.forEach(key => newSelected.delete(key));
    } else {
      providerModelKeys.forEach(key => newSelected.add(key));
    }
    setSelectedFreeModeModels(newSelected);
  };

  const toggleFreeModeModel = (provider: string, modelValue: string) => {
    const key = `${provider}:${modelValue}`;
    const newSelected = new Set(selectedFreeModeModels);
    if (newSelected.has(key)) {
      newSelected.delete(key);
    } else {
      newSelected.add(key);
    }
    setSelectedFreeModeModels(newSelected);
  };

  const toggleExpandProvider = (provider: string) => {
    const newExpanded = new Set(expandedProviders);
    if (newExpanded.has(provider)) {
      newExpanded.delete(provider);
    } else {
      newExpanded.add(provider);
    }
    setExpandedProviders(newExpanded);
  };

  // Check functions for revolver mode
  const isRevolverProviderFullySelected = (provider: string): boolean => {
    const providerModels = models[provider] || [];
    if (providerModels.length === 0) return false;
    return providerModels.every(m => selectedRevolverModels.has(`${provider}:${m.value}`));
  };

  const isRevolverProviderPartiallySelected = (provider: string): boolean => {
    const providerModels = models[provider] || [];
    if (providerModels.length === 0) return false;
    const selectedCount = providerModels.filter(m => selectedRevolverModels.has(`${provider}:${m.value}`)).length;
    return selectedCount > 0 && selectedCount < providerModels.length;
  };

  const getRevolverSelectedCountForProvider = (provider: string): number => {
    const providerModels = models[provider] || [];
    return providerModels.filter(m => selectedRevolverModels.has(`${provider}:${m.value}`)).length;
  };

  // Check functions for free mode
  const isFreeModeProviderFullySelected = (provider: string): boolean => {
    const providerModels = models[provider] || [];
    if (providerModels.length === 0) return false;
    return providerModels.every(m => selectedFreeModeModels.has(`${provider}:${m.value}`));
  };

  const isFreeModeProviderPartiallySelected = (provider: string): boolean => {
    const providerModels = models[provider] || [];
    if (providerModels.length === 0) return false;
    const selectedCount = providerModels.filter(m => selectedFreeModeModels.has(`${provider}:${m.value}`)).length;
    return selectedCount > 0 && selectedCount < providerModels.length;
  };

  const getFreeModeSelectedCountForProvider = (provider: string): number => {
    const providerModels = models[provider] || [];
    return providerModels.filter(m => selectedFreeModeModels.has(`${provider}:${m.value}`)).length;
  };

  const handleLockToggle = () => {
    // Don't allow turning off lock mode if it's the only mode active
    if (modelLocked && !revolverMode && !freeMode) {
      return; // Can't turn off - at least one mode must be on
    }
    const newLocked = !modelLocked;
    setModelLocked(newLocked);
    if (newLocked) {
      // Lock disables the other modes
      setRevolverMode(false);
      setFreeMode(false);
    }
  };

  const handleRevolverToggle = () => {
    const newRevolver = !revolverMode;
    setRevolverMode(newRevolver);
    if (newRevolver) {
      // Revolver disables the other modes
      setModelLocked(false);
      setFreeMode(false);
    } else {
      // Default to lock mode when revolver is turned off
      setModelLocked(true);
    }
  };

  const handleFreeModeToggle = () => {
    const newFreeMode = !freeMode;
    setFreeMode(newFreeMode);
    if (newFreeMode) {
      // Free mode disables the other modes
      setModelLocked(false);
      setRevolverMode(false);
    } else {
      // Default to lock mode when free mode is turned off
      setModelLocked(true);
    }
  };

  const handleSave = async () => {
    if (!userId) return;
    setSaving(true);
    try {
      // Save lock state if changed
      if (modelLocked !== initialModelLocked) {
        await invoke('set_model_lock', {
          userId,
          qubeId,
          locked: modelLocked,
          modelName: modelLocked ? currentModel : null,
        });
      }

      // Save revolver state if changed
      if (revolverMode !== initialRevolverMode) {
        await invoke('set_revolver_mode', {
          userId,
          qubeId,
          enabled: revolverMode,
        });
      }

      // Save free mode state
      await invoke('set_free_mode', {
        userId,
        qubeId,
        enabled: freeMode,
      });

      // Helper to extract model IDs from selected set
      const extractModelsToSave = (selectedSet: Set<string>): { models: string[], providers: string[] } => {
        const availableProviders = getAvailableProviders();
        const allPossibleModels = new Set<string>();
        availableProviders.forEach(provider => {
          const providerModels = models[provider] || [];
          providerModels.forEach(m => allPossibleModels.add(`${provider}:${m.value}`));
        });

        // Check if all models are selected
        const allSelected = allPossibleModels.size === selectedSet.size &&
          [...allPossibleModels].every(m => selectedSet.has(m));

        if (allSelected) {
          return { models: [], providers: [] };
        }

        const modelsToSave: string[] = [];
        const providersToSave: string[] = [];
        selectedSet.forEach(key => {
          const [provider, ...modelParts] = key.split(':');
          const modelId = modelParts.join(':');
          modelsToSave.push(modelId);
          if (!providersToSave.includes(provider)) {
            providersToSave.push(provider);
          }
        });
        return { models: modelsToSave, providers: providersToSave };
      };

      // Save revolver models
      const revolverResult = extractModelsToSave(selectedRevolverModels);
      await invoke('set_revolver_models', {
        userId,
        qubeId,
        models: revolverResult.models,
      });
      await invoke('set_revolver_providers', {
        userId,
        qubeId,
        providers: revolverResult.providers,
      });

      // Save free mode models
      const freeModeResult = extractModelsToSave(selectedFreeModeModels);
      await invoke('set_free_mode_models', {
        userId,
        qubeId,
        models: freeModeResult.models,
      });

      // Notify parent of changes
      onUpdate({
        modelLocked,
        lockedToModel: modelLocked ? currentModel : null,
        revolverMode,
        revolverProviders: revolverResult.providers,
        revolverModels: revolverResult.models,
        freeMode,
        freeModeModels: freeModeResult.models,
      });

      onClose();
    } catch (error) {
      console.error('Failed to save settings:', error);
    } finally {
      setSaving(false);
    }
  };

  const availableProviders = getAvailableProviders();

  // Check if everything is loaded
  const isReady = isLoaded && !loadingProviders;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <GlassCard
        className={`w-full max-w-lg max-h-[85vh] p-6 m-4 overflow-hidden flex flex-col transition-all ${
          freeMode ? 'ring-2 ring-purple-500' : revolverMode ? 'ring-2 ring-green-500' : ''
        }`}
        onClick={(e: React.MouseEvent) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-display text-accent-primary">
            Model Settings
          </h2>
          <button onClick={onClose} className="text-text-tertiary hover:text-text-primary text-xl">
            &times;
          </button>
        </div>

        <p className="text-text-secondary text-sm mb-4">
          Configure model behavior for <span className="text-text-primary font-medium">{qubeName}</span>
        </p>

        {/* Loading State */}
        {!isReady ? (
          <div className="flex-1 flex items-center justify-center py-12">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-2 border-accent-primary border-t-transparent rounded-full animate-spin" />
              <p className="text-text-tertiary text-sm">Loading models...</p>
            </div>
          </div>
        ) : (
        /* Content */
        <div className="flex-1 overflow-y-auto space-y-6 pr-2">
          {/* Manual Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-2xl">{modelLocked ? '🔒' : '🔓'}</span>
                <h3 className="text-base font-semibold text-text-primary">Manual</h3>
              </div>
              <button
                onClick={handleLockToggle}
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  modelLocked ? 'bg-green-500' : 'bg-red-500/60'
                }`}
              >
                <span
                  className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                    modelLocked ? 'left-7' : 'left-1'
                  }`}
                />
              </button>
            </div>
            <p className="text-text-tertiary text-xs">
              Prevent the qube from switching to a different AI model during conversations.
            </p>
            <div className={`mt-2 p-2 rounded-lg border ${
              modelLocked
                ? 'bg-green-500/10 border-green-500/30'
                : 'bg-glass-bg/50 border-glass-border'
            }`}>
              <p className={`text-xs ${modelLocked ? 'text-green-400' : 'text-text-secondary'}`}>
                {modelLocked ? 'Locked to: ' : 'Will lock to: '}
                <span className="font-medium">{formatModelName(currentModel)}</span>
              </p>
            </div>
          </div>

          {/* Divider */}
          <div className="border-t border-glass-border" />

          {/* Revolver Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-2xl">🎰</span>
                <h3 className="text-base font-semibold text-text-primary">Revolver</h3>
              </div>
              <button
                onClick={handleRevolverToggle}
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  revolverMode ? 'bg-green-500' : 'bg-red-500/60'
                }`}
              >
                <span
                  className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                    revolverMode ? 'left-7' : 'left-1'
                  }`}
                />
              </button>
            </div>
            <p className="text-text-tertiary text-xs">
              Rotate between different AI models for each response. Enhances privacy by distributing queries.
            </p>

            {revolverMode && (
              <div className="mt-3 space-y-2">
                <label className="text-text-secondary text-xs block mb-2">
                  Select models to include in rotation:
                </label>
                {loadingProviders ? (
                  <p className="text-text-tertiary text-xs">Loading providers...</p>
                ) : availableProviders.length === 0 ? (
                  <p className="text-text-tertiary text-xs">No providers configured. Add API keys in Settings.</p>
                ) : (
                  <div className="space-y-1">
                    {availableProviders.map((provider) => {
                      const providerModels = models[provider] || [];
                      const isExpanded = expandedProviders.has(provider);
                      const isFullySelected = isRevolverProviderFullySelected(provider);
                      const isPartiallySelected = isRevolverProviderPartiallySelected(provider);
                      const selectedCount = getRevolverSelectedCountForProvider(provider);

                      return (
                        <div key={provider} className="border border-glass-border rounded-lg overflow-hidden">
                          {/* Provider Header */}
                          <div
                            className="flex items-center gap-2 p-2 bg-glass-bg/50 cursor-pointer hover:bg-glass-bg/80"
                            onClick={() => toggleExpandProvider(provider)}
                          >
                            <span className="text-text-tertiary text-xs">
                              {isExpanded ? '▼' : '▶'}
                            </span>
                            <input
                              type="checkbox"
                              checked={isFullySelected}
                              ref={(el) => {
                                if (el) el.indeterminate = isPartiallySelected;
                              }}
                              onChange={(e) => {
                                e.stopPropagation();
                                toggleRevolverProvider(provider);
                              }}
                              onClick={(e) => e.stopPropagation()}
                              className="rounded border-glass-border bg-glass-bg text-cyan-500 focus:ring-cyan-500"
                            />
                            <span className="text-text-primary text-sm font-medium flex-1">
                              {PROVIDER_LABELS[provider] || provider}
                            </span>
                            <span className="text-text-tertiary text-xs">
                              {selectedCount}/{providerModels.length}
                            </span>
                          </div>

                          {/* Models List (Collapsible) */}
                          {isExpanded && providerModels.length > 0 && (
                            <div className="p-2 pl-8 space-y-1 bg-black/20 max-h-48 overflow-y-auto">
                              {providerModels.map((model) => (
                                <label
                                  key={model.value}
                                  className="flex items-center gap-2 text-xs cursor-pointer py-1 hover:bg-glass-bg/30 px-1 rounded"
                                >
                                  <input
                                    type="checkbox"
                                    checked={selectedRevolverModels.has(`${provider}:${model.value}`)}
                                    onChange={() => toggleRevolverModel(provider, model.value)}
                                    className="rounded border-glass-border bg-glass-bg text-cyan-500 focus:ring-cyan-500"
                                  />
                                  <span className="text-text-primary">{model.label}</span>
                                </label>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
                <p className="text-text-tertiary text-xs italic mt-2">
                  {selectedRevolverModels.size} model{selectedRevolverModels.size !== 1 ? 's' : ''} selected for rotation
                </p>
              </div>
            )}
          </div>

          {/* Divider */}
          <div className="border-t border-glass-border" />

          {/* Autonomous Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-2xl">🧠</span>
                <h3 className="text-base font-semibold text-text-primary">Autonomous</h3>
              </div>
              <button
                onClick={handleFreeModeToggle}
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  freeMode ? 'bg-green-500' : 'bg-red-500/60'
                }`}
              >
                <span
                  className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                    freeMode ? 'left-7' : 'left-1'
                  }`}
                />
              </button>
            </div>
            <p className="text-text-tertiary text-xs">
              Autonomously choose from selected models based on the task.
            </p>

            {freeMode && (
              <div className="mt-3 space-y-2">
                <label className="text-text-secondary text-xs block mb-2">
                  Select models available for autonomous selection:
                </label>
                {loadingProviders ? (
                  <p className="text-text-tertiary text-xs">Loading providers...</p>
                ) : availableProviders.length === 0 ? (
                  <p className="text-text-tertiary text-xs">No providers configured. Add API keys in Settings.</p>
                ) : (
                  <div className="space-y-1">
                    {availableProviders.map((provider) => {
                      const providerModels = models[provider] || [];
                      const isExpanded = expandedProviders.has(provider);
                      const isFullySelected = isFreeModeProviderFullySelected(provider);
                      const isPartiallySelected = isFreeModeProviderPartiallySelected(provider);
                      const selectedCount = getFreeModeSelectedCountForProvider(provider);

                      return (
                        <div key={`free-${provider}`} className="border border-glass-border rounded-lg overflow-hidden">
                          {/* Provider Header */}
                          <div
                            className="flex items-center gap-2 p-2 bg-glass-bg/50 cursor-pointer hover:bg-glass-bg/80"
                            onClick={() => toggleExpandProvider(provider)}
                          >
                            <span className="text-text-tertiary text-xs">
                              {isExpanded ? '▼' : '▶'}
                            </span>
                            <input
                              type="checkbox"
                              checked={isFullySelected}
                              ref={(el) => {
                                if (el) el.indeterminate = isPartiallySelected;
                              }}
                              onChange={(e) => {
                                e.stopPropagation();
                                toggleFreeModeProvider(provider);
                              }}
                              onClick={(e) => e.stopPropagation()}
                              className="rounded border-glass-border bg-glass-bg text-purple-500 focus:ring-purple-500"
                            />
                            <span className="text-text-primary text-sm font-medium flex-1">
                              {PROVIDER_LABELS[provider] || provider}
                            </span>
                            <span className="text-text-tertiary text-xs">
                              {selectedCount}/{providerModels.length}
                            </span>
                          </div>

                          {/* Models List (Collapsible) */}
                          {isExpanded && providerModels.length > 0 && (
                            <div className="p-2 pl-8 space-y-1 bg-black/20 max-h-48 overflow-y-auto">
                              {providerModels.map((model) => (
                                <label
                                  key={model.value}
                                  className="flex items-center gap-2 text-xs cursor-pointer py-1 hover:bg-glass-bg/30 px-1 rounded"
                                >
                                  <input
                                    type="checkbox"
                                    checked={selectedFreeModeModels.has(`${provider}:${model.value}`)}
                                    onChange={() => toggleFreeModeModel(provider, model.value)}
                                    className="rounded border-glass-border bg-glass-bg text-purple-500 focus:ring-purple-500"
                                  />
                                  <span className="text-text-primary">{model.label}</span>
                                </label>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
                <p className="text-text-tertiary text-xs italic mt-2">
                  {selectedFreeModeModels.size} model{selectedFreeModeModels.size !== 1 ? 's' : ''} available for selection
                </p>
              </div>
            )}
          </div>
        </div>
        )}

        {/* Footer */}
        <div className="flex justify-end gap-3 mt-4 pt-4 border-t border-glass-border">
          <GlassButton variant="secondary" onClick={onClose} size="sm">
            Cancel
          </GlassButton>
          <GlassButton variant="primary" onClick={handleSave} loading={saving} size="sm">
            Save Changes
          </GlassButton>
        </div>
      </GlassCard>
    </div>
  );
};
