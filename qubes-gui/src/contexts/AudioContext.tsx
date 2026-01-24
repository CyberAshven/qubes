import React, { createContext, useContext, useRef, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';

interface AudioContextType {
  playTTS: (userId: string, qubeId: string, text: string, password: string) => Promise<void>;
  prefetchTTS: (userId: string, qubeId: string, text: string, password: string) => Promise<string>;
  playPrefetchedTTS: (base64Audio: string, text: string) => Promise<void>;
  stopAudio: () => void;
  isPlaying: boolean;
  audioElement: HTMLAudioElement | null;
  // Multi-chunk playback info for TypewriterText sync
  totalChunks: number;
  currentChunk: number;
  isLastChunk: boolean;
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
  total_chunks?: number;
  qube_id?: string;
  error?: string;
}

export const AudioProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = React.useState(false);
  const [audioElement, setAudioElement] = React.useState<HTMLAudioElement | null>(null);
  const lastPlayedTextRef = useRef<string>('');

  // Multi-chunk playback state
  const chunkQueueRef = useRef<string[]>([]);
  const currentChunkIndexRef = useRef<number>(0);

  // Expose chunk info for TypewriterText sync
  const [totalChunks, setTotalChunks] = React.useState(1);
  const [currentChunk, setCurrentChunk] = React.useState(1);
  const [isLastChunk, setIsLastChunk] = React.useState(true);

  // Initialize audio element if it doesn't exist
  React.useEffect(() => {
    if (!audioRef.current) {
      audioRef.current = new Audio();

      // Handle audio ended - play next chunk if available
      audioRef.current.addEventListener('ended', () => {
        const nextChunkIndex = currentChunkIndexRef.current + 1;

        // Check if there are more chunks to play
        if (nextChunkIndex < chunkQueueRef.current.length) {
          currentChunkIndexRef.current = nextChunkIndex;
          const nextChunkPath = chunkQueueRef.current[nextChunkIndex];

          console.log(`Playing chunk ${nextChunkIndex + 1} of ${chunkQueueRef.current.length}`);

          // Update chunk state for TypewriterText
          setCurrentChunk(nextChunkIndex + 1);
          setIsLastChunk(nextChunkIndex + 1 >= chunkQueueRef.current.length);

          // Load and play next chunk
          audioRef.current!.src = nextChunkPath;
          audioRef.current!.play().catch(err => {
            console.error('Failed to play next chunk:', err);
            setIsPlaying(false);
            // Clear chunk queue on error
            chunkQueueRef.current = [];
            currentChunkIndexRef.current = 0;
            setTotalChunks(1);
            setCurrentChunk(1);
            setIsLastChunk(true);
          });
        } else {
          // No more chunks, playback complete
          setIsPlaying(false);
          chunkQueueRef.current = [];
          currentChunkIndexRef.current = 0;
          setTotalChunks(1);
          setCurrentChunk(1);
          setIsLastChunk(true);
        }
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
      // Clear chunk queue on unmount
      chunkQueueRef.current = [];
      currentChunkIndexRef.current = 0;
    };
  }, []);

  const playTTS = useCallback(async (userId: string, qubeId: string, text: string, password: string) => {
    // Skip if we've already played this exact text
    if (lastPlayedTextRef.current === text) {
      return;
    }

    try {
      const speechResponse = await invoke<SpeechResponse>('generate_speech', {
        userId,
        qubeId,
        text,
        password
      });

      if (speechResponse.success && speechResponse.audio_path) {
        const numChunks = speechResponse.total_chunks || 1;

        // Build array of all chunk paths
        const chunkPaths: string[] = [];

        for (let i = 1; i <= numChunks; i++) {
          let chunkFilePath = speechResponse.audio_path;

          // For multi-chunk audio, replace or append chunk suffix
          if (numChunks > 1) {
            // Replace _chunk_1 with _chunk_N, or append _chunk_N if not present
            if (chunkFilePath.includes('_chunk_1')) {
              chunkFilePath = chunkFilePath.replace('_chunk_1', `_chunk_${i}`);
            } else {
              // Shouldn't happen with new backend, but handle legacy case
              const extension = chunkFilePath.substring(chunkFilePath.lastIndexOf('.'));
              const basePath = chunkFilePath.substring(0, chunkFilePath.lastIndexOf('.'));
              chunkFilePath = `${basePath}_chunk_${i}${extension}`;
            }
          }

          // Get base64 data for this chunk
          const base64Audio = await invoke<string>('get_audio_base64', {
            filePath: chunkFilePath
          });

          chunkPaths.push(base64Audio);
        }

        if (numChunks > 1) {
          console.log(`Multi-chunk audio: ${numChunks} chunks`);
        }

        // Set up chunk queue for sequential playback
        chunkQueueRef.current = chunkPaths;
        currentChunkIndexRef.current = 0;

        // Update chunk state for TypewriterText sync
        setTotalChunks(numChunks);
        setCurrentChunk(1);
        setIsLastChunk(numChunks <= 1);

        if (audioRef.current) {
          // Reset audio element to clear any stale state (ended, error, etc.)
          audioRef.current.pause();
          audioRef.current.currentTime = 0;
          audioRef.current.removeAttribute('src');
          audioRef.current.load(); // This resets the audio element state

          // Set the first chunk
          audioRef.current.src = chunkPaths[0];

          audioRef.current.addEventListener('error', (e) => {
            console.error('Audio element error:', e);
            console.error('Audio error details:', audioRef.current?.error);
            // Clear chunk queue on error
            chunkQueueRef.current = [];
            currentChunkIndexRef.current = 0;
            setTotalChunks(1);
            setCurrentChunk(1);
            setIsLastChunk(true);
          }, { once: true });

          // Start playing first chunk immediately
          await audioRef.current.play();

          // Mark this text as played
          lastPlayedTextRef.current = text;
        }
      } else {
        console.error('TTS generation failed:', speechResponse.error);
        throw new Error(`TTS generation failed: ${speechResponse.error}`);
      }
    } catch (err) {
      console.error('TTS error:', err);
      // Clear chunk queue on error
      chunkQueueRef.current = [];
      currentChunkIndexRef.current = 0;
      setTotalChunks(1);
      setCurrentChunk(1);
      setIsLastChunk(true);
      throw err;
    }
  }, []);

  const prefetchTTS = useCallback(async (userId: string, qubeId: string, text: string, password: string): Promise<string> => {
    try {
      const speechResponse = await invoke<SpeechResponse>('generate_speech', {
        userId,
        qubeId,
        text,
        password
      });

      if (speechResponse.success && speechResponse.audio_path) {
        // Get audio as base64 data URL from Tauri backend
        const base64Audio = await invoke<string>('get_audio_base64', {
          filePath: speechResponse.audio_path
        });

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
      return;
    }

    try {
      // Reset chunk state for single-chunk prefetched audio
      setTotalChunks(1);
      setCurrentChunk(1);
      setIsLastChunk(true);
      chunkQueueRef.current = [];
      currentChunkIndexRef.current = 0;

      if (audioRef.current) {
        // Reset audio element to clear any stale state (ended, error, etc.)
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
        audioRef.current.removeAttribute('src');
        audioRef.current.load(); // This resets the audio element state

        // Now set the new src
        audioRef.current.src = base64Audio;

        audioRef.current.addEventListener('error', (e) => {
          console.error('Prefetched audio element error:', e);
          console.error('Audio error details:', audioRef.current?.error);
        }, { once: true });

        // Start playing prefetched audio immediately
        await audioRef.current.play();

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
    // Clear chunk queue when manually stopping
    chunkQueueRef.current = [];
    currentChunkIndexRef.current = 0;
    setTotalChunks(1);
    setCurrentChunk(1);
    setIsLastChunk(true);
  }, []);

  const value = {
    playTTS,
    prefetchTTS,
    playPrefetchedTTS,
    stopAudio,
    isPlaying,
    audioElement,
    totalChunks,
    currentChunk,
    isLastChunk,
  };

  return <AudioContext.Provider value={value}>{children}</AudioContext.Provider>;
};
