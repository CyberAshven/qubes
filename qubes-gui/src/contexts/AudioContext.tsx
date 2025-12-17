import React, { createContext, useContext, useRef, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';

interface AudioContextType {
  playTTS: (userId: string, qubeId: string, text: string, password: string) => Promise<void>;
  prefetchTTS: (userId: string, qubeId: string, text: string, password: string) => Promise<string>;
  playPrefetchedTTS: (base64Audio: string, text: string) => Promise<void>;
  stopAudio: () => void;
  isPlaying: boolean;
  audioElement: HTMLAudioElement | null;
}

const AudioContext = createContext<AudioContextType | undefined>(undefined);

export const useAudio = () => {
  const context = useContext(AudioContext);
  if (!context) {
    throw new Error('useAudio must be used within AudioProvider');
  }
  return context;
};

interface SpeechResponse {
  success: boolean;
  audio_path?: string;
  qube_id?: string;
  error?: string;
}

export const AudioProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = React.useState(false);
  const [audioElement, setAudioElement] = React.useState<HTMLAudioElement | null>(null);
  const lastPlayedTextRef = useRef<string>('');

  // Initialize audio element if it doesn't exist
  React.useEffect(() => {
    if (!audioRef.current) {
      audioRef.current = new Audio();
      audioRef.current.addEventListener('ended', () => {
        setIsPlaying(false);
      });
      audioRef.current.addEventListener('pause', () => {
        setIsPlaying(false);
      });
      audioRef.current.addEventListener('play', () => {
        setIsPlaying(true);
      });

      // Make audio element available in state so context consumers get notified
      setAudioElement(audioRef.current);
    }

    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = '';
      }
    };
  }, []);

  const playTTS = useCallback(async (userId: string, qubeId: string, text: string, password: string) => {
    // Skip if we've already played this exact text
    if (lastPlayedTextRef.current === text) {
      console.log('TTS already played for this response, skipping');
      return;
    }

    try {
      console.log('Generating TTS for:', text.substring(0, 50) + '...');

      const speechResponse = await invoke<SpeechResponse>('generate_speech', {
        userId,
        qubeId,
        text,
        password
      });

      if (speechResponse.success && speechResponse.audio_path) {
        console.log('TTS generated, audio path:', speechResponse.audio_path);

        // Get audio as base64 data URL from Tauri backend
        const base64Audio = await invoke<string>('get_audio_base64', {
          filePath: speechResponse.audio_path
        });

        console.log('Got base64 audio data URL (length:', base64Audio.length, ')');

        if (audioRef.current) {
          // Reset audio element to clear any stale state (ended, error, etc.)
          console.log('[AudioContext] Resetting audio element before loading new audio');
          audioRef.current.pause();
          audioRef.current.currentTime = 0;
          audioRef.current.removeAttribute('src');
          audioRef.current.load(); // This resets the audio element state

          // Now set the new src
          audioRef.current.src = base64Audio;

          audioRef.current.addEventListener('loadeddata', () => {
            console.log('Audio loaded successfully - ready to play');
          }, { once: true });

          audioRef.current.addEventListener('error', (e) => {
            console.error('Audio element error:', e);
            console.error('Audio error details:', audioRef.current?.error);
          }, { once: true });

          // Start playing audio immediately
          console.log('Audio loaded, starting playback...');
          await audioRef.current.play();
          console.log('Audio playing');

          // Mark this text as played
          lastPlayedTextRef.current = text;
        }
      } else {
        console.error('TTS generation failed:', speechResponse.error);
        throw new Error(`TTS generation failed: ${speechResponse.error}`);
      }
    } catch (err) {
      console.error('TTS error:', err);
      throw err;
    }
  }, []);

  const prefetchTTS = useCallback(async (userId: string, qubeId: string, text: string, password: string): Promise<string> => {
    try {
      console.log('Prefetching TTS for:', text.substring(0, 50) + '...');

      const speechResponse = await invoke<SpeechResponse>('generate_speech', {
        userId,
        qubeId,
        text,
        password
      });

      if (speechResponse.success && speechResponse.audio_path) {
        console.log('TTS prefetched, audio path:', speechResponse.audio_path);

        // Get audio as base64 data URL from Tauri backend
        const base64Audio = await invoke<string>('get_audio_base64', {
          filePath: speechResponse.audio_path
        });

        console.log('Prefetched TTS base64 audio (length:', base64Audio.length, ')');
        return base64Audio;
      } else {
        console.error('TTS prefetch failed:', speechResponse.error);
        throw new Error(`TTS prefetch failed: ${speechResponse.error}`);
      }
    } catch (err) {
      console.error('TTS prefetch error:', err);
      throw err;
    }
  }, []);

  const playPrefetchedTTS = useCallback(async (base64Audio: string, text: string): Promise<void> => {
    // Skip if we've already played this exact text
    if (lastPlayedTextRef.current === text) {
      console.log('TTS already played for this response, skipping');
      return;
    }

    try {
      console.log('Playing prefetched TTS audio');

      if (audioRef.current) {
        // Reset audio element to clear any stale state (ended, error, etc.)
        console.log('[AudioContext] Resetting audio element before loading prefetched audio');
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
        audioRef.current.removeAttribute('src');
        audioRef.current.load(); // This resets the audio element state

        // Now set the new src
        audioRef.current.src = base64Audio;

        audioRef.current.addEventListener('loadeddata', () => {
          console.log('Prefetched audio loaded successfully - ready to play');
        }, { once: true });

        audioRef.current.addEventListener('error', (e) => {
          console.error('Prefetched audio element error:', e);
          console.error('Audio error details:', audioRef.current?.error);
        }, { once: true });

        // Start playing prefetched audio immediately
        console.log('Prefetched audio loaded, starting playback...');
        await audioRef.current.play();
        console.log('Prefetched audio playing');

        // Mark this text as played
        lastPlayedTextRef.current = text;
      }
    } catch (err) {
      console.error('Prefetched TTS playback error:', err);
      throw err;
    }
  }, []);

  const stopAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsPlaying(false);
    }
  }, []);

  const value = {
    playTTS,
    prefetchTTS,
    playPrefetchedTTS,
    stopAudio,
    isPlaying,
    audioElement, // Use state value instead of ref
  };

  return <AudioContext.Provider value={value}>{children}</AudioContext.Provider>;
};
