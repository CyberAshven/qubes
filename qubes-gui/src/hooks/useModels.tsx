import { create } from 'zustand';
import { invoke } from '@tauri-apps/api/core';
import { formatModelName as fallbackFormatModelName } from '../utils/modelFormatter';

interface ModelInfo {
  value: string;
  label: string;
  description?: string;
}

interface ProviderInfo {
  value: string;
  label: string;
}

interface AvailableModelsResponse {
  providers: ProviderInfo[];
  models: Record<string, ModelInfo[]>;
  defaults: Record<string, string>;
}

interface ModelsState {
  providers: ProviderInfo[];
  models: Record<string, ModelInfo[]>;
  defaults: Record<string, string>;
  isLoading: boolean;
  error: string | null;
  isLoaded: boolean;
  fetchModels: () => Promise<void>;
  getModelsForProvider: (provider: string) => ModelInfo[];
  getDefaultModel: (provider: string) => string;
  formatModelName: (modelId: string) => string;
}

export const useModels = create<ModelsState>((set, get) => ({
  providers: [],
  models: {},
  defaults: {},
  isLoading: false,
  error: null,
  isLoaded: false,

  fetchModels: async () => {
    // Only fetch once
    if (get().isLoaded || get().isLoading) return;

    set({ isLoading: true, error: null });
    try {
      const response = await invoke<AvailableModelsResponse>('get_available_models');

      set({
        providers: response.providers,
        models: response.models,
        defaults: response.defaults,
        isLoading: false,
        isLoaded: true,
      });
    } catch (error) {
      console.error('Failed to fetch models:', error);
      set({
        isLoading: false,
        error: String(error),
      });
    }
  },

  getModelsForProvider: (provider: string) => {
    return get().models[provider] || [];
  },

  getDefaultModel: (provider: string) => {
    return get().defaults[provider] || '';
  },

  formatModelName: (modelId: string) => {
    const { models, isLoaded } = get();

    // If not loaded yet, use fallback
    if (!isLoaded) {
      return fallbackFormatModelName(modelId);
    }

    // Search through all models to find the label
    for (const providerModels of Object.values(models)) {
      const found = providerModels.find(m => m.value === modelId);
      if (found) return found.label;
    }

    // Fallback to existing formatModelName utility
    return fallbackFormatModelName(modelId);
  },
}));
