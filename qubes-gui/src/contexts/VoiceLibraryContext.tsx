import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useAuth } from '../hooks/useAuth';

interface VoiceLibraryEntry {
  name: string;
  voice_type: 'designed' | 'cloned';
  created_at: string;
  language: string;
  design_prompt?: string;
  clone_audio_path?: string;
  clone_audio_text?: string;
}

interface VoiceLibraryContextType {
  voiceLibrary: Record<string, VoiceLibraryEntry>;
  refreshVoiceLibrary: () => Promise<void>;
  isLoading: boolean;
}

const VoiceLibraryContext = createContext<VoiceLibraryContextType | null>(null);

export const VoiceLibraryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { userId } = useAuth();
  const [voiceLibrary, setVoiceLibrary] = useState<Record<string, VoiceLibraryEntry>>({});
  const [isLoading, setIsLoading] = useState(false);

  const refreshVoiceLibrary = useCallback(async () => {
    if (!userId) return;

    setIsLoading(true);
    try {
      const result = await invoke<{ success: boolean; voice_library?: Record<string, VoiceLibraryEntry> }>('get_voice_library', { userId });
      if (result.success && result.voice_library) {
        console.log('[VoiceLibraryContext] Refreshed voice library:', Object.keys(result.voice_library).length, 'voices');
        setVoiceLibrary(result.voice_library);
      }
    } catch (error) {
      console.error('[VoiceLibraryContext] Failed to load voice library:', error);
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  // Load voice library on mount and when userId changes
  useEffect(() => {
    if (userId) {
      refreshVoiceLibrary();
    }
  }, [userId, refreshVoiceLibrary]);

  return (
    <VoiceLibraryContext.Provider value={{ voiceLibrary, refreshVoiceLibrary, isLoading }}>
      {children}
    </VoiceLibraryContext.Provider>
  );
};

export const useVoiceLibrary = () => {
  const context = useContext(VoiceLibraryContext);
  if (!context) {
    throw new Error('useVoiceLibrary must be used within a VoiceLibraryProvider');
  }
  return context;
};
