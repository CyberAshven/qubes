import React, { createContext, useContext, useRef, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen, type UnlistenFn } from '@tauri-apps/api/event';

// Minimal interface matching the HTMLAudioElement properties that TypewriterText uses.
// Implemented by NativeAudioPlayer (all platforms via Rust native audio playback).
export interface AudioPlaybackElement {
  readonly currentTime: number;
  readonly duration: number;
  readonly paused: boolean;
  readonly ended: boolean;
  readonly readyState: number;
  readonly error: { code: number; message: string } | null;
  src: string;
  addEventListener(event: string, handler: EventListenerOrEventListenerObject): void;
  removeEventListener(event: string, handler: EventListenerOrEventListenerObject): void;
}

interface AudioContextType {
  playTTS: (userId: string, qubeId: string, text: string, password: string) => Promise<void>;
  prefetchTTS: (userId: string, qubeId: string, text: string, password: string) => Promise<string>;
  playPrefetchedTTS: (blobUrl: string, text: string) => Promise<void>;
  stopAudio: () => void;
  isPlaying: boolean;
  audioElement: AudioPlaybackElement | null;
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

interface NativePlayResult {
  duration: number;
  player: string;
}

// Timer-based player for native audio playback (pw-play/aplay/afplay).
// Doesn't play audio itself - that's done by the Rust side via system commands.
// Tracks timing so TypewriterText can sync text animation to the audio.
class NativeAudioPlayer extends EventTarget implements AudioPlaybackElement {
  // Text leads audio by this many seconds (typewriter shows text before you hear it)
  private static readonly TEXT_LEAD_SECS = 0.75;

  private _duration: number = 0;
  private _startTime: number = 0;
  private _paused: boolean = true;
  private _ended: boolean = false;
  private _error: { code: number; message: string } | null = null;
  src: string = '';

  get currentTime(): number {
    if (this._paused || this._ended) return this._ended ? this._duration : 0;
    const elapsed = (performance.now() - this._startTime) / 1000;
    return Math.min(elapsed + NativeAudioPlayer.TEXT_LEAD_SECS, this._duration);
  }

  get duration(): number { return this._duration || NaN; }
  get paused(): boolean { return this._paused; }
  get ended(): boolean { return this._ended; }
  get readyState(): number { return this._duration > 0 ? 4 : 0; }
  get error(): { code: number; message: string } | null { return this._error; }

  // Set duration from WAV header (parsed by Rust)
  setDuration(duration: number): void {
    this._duration = duration;
    this._ended = false;
    this._paused = true;
    this._error = null;
    this.dispatchEvent(new Event('durationchange'));
  }

  // Start the timer (call after native playback is confirmed started)
  startPlayback(): void {
    this._startTime = performance.now();
    this._paused = false;
    this._ended = false;
    this._error = null;
    this.dispatchEvent(new Event('play'));
  }

  // Called when the Rust side signals playback ended
  markEnded(): void {
    this._ended = true;
    this._paused = true;
    this.dispatchEvent(new Event('ended'));
  }

  // Stop tracking
  stop(): void {
    this._paused = true;
    this.dispatchEvent(new Event('pause'));
  }

  // Reset for new audio
  reset(): void {
    this._duration = 0;
    this._startTime = 0;
    this._paused = true;
    this._ended = false;
    this._error = null;
    this.src = '';
  }
}

export const AudioProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const playerRef = useRef<NativeAudioPlayer | null>(null);
  const [isPlaying, setIsPlaying] = React.useState(false);
  const [audioElement, setAudioElement] = React.useState<AudioPlaybackElement | null>(null);
  const lastPlayedTextRef = useRef<string>('');
  const unlistenRef = useRef<UnlistenFn | null>(null);

  // Multi-chunk playback state
  const chunkPathsRef = useRef<string[]>([]);
  const currentChunkIndexRef = useRef<number>(0);
  const playbackTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [totalChunks, setTotalChunks] = React.useState(1);
  const [currentChunk, setCurrentChunk] = React.useState(1);
  const [isLastChunk, setIsLastChunk] = React.useState(true);

  const clearPlaybackTimeout = () => {
    if (playbackTimeoutRef.current) {
      clearTimeout(playbackTimeoutRef.current);
      playbackTimeoutRef.current = null;
    }
  };

  const resetChunkState = () => {
    chunkPathsRef.current = [];
    currentChunkIndexRef.current = 0;
    clearPlaybackTimeout();
    setTotalChunks(1);
    setCurrentChunk(1);
    setIsLastChunk(true);
  };

  // Safety timeout: if audio-playback-ended is never emitted (player crash, thread panic),
  // auto-recover after duration + 10 seconds to prevent permanently stuck "playing" state.
  const startPlaybackTimeout = (durationSecs: number) => {
    clearPlaybackTimeout();
    const timeoutMs = (durationSecs + 10) * 1000;
    playbackTimeoutRef.current = setTimeout(() => {
      console.warn(`[AudioContext] Safety timeout: audio-playback-ended not received after ${durationSecs + 10}s, recovering`);
      const player = playerRef.current;
      if (player) {
        player.markEnded();
      }
      setIsPlaying(false);
      resetChunkState();
    }, timeoutMs);
  };

  // Play a single audio file natively and set up the timer
  const playFileNative = async (filePath: string): Promise<number> => {
    const player = playerRef.current;
    if (!player) throw new Error('Player not initialized');

    const result = await invoke<NativePlayResult>('play_audio_native', { filePath });
    player.setDuration(result.duration);
    player.startPlayback();
    startPlaybackTimeout(result.duration);
    return result.duration;
  };

  // Initialize NativeAudioPlayer and listen for playback-ended events
  React.useEffect(() => {
    if (!playerRef.current) {
      const player = new NativeAudioPlayer();

      player.addEventListener('play', () => setIsPlaying(true));
      player.addEventListener('pause', () => setIsPlaying(false));

      playerRef.current = player;
      setAudioElement(player);
    }

    // Listen for native audio playback ending
    let mounted = true;
    listen('audio-playback-ended', () => {
      if (!mounted) return;
      clearPlaybackTimeout();
      const player = playerRef.current;
      if (!player) return;

      const nextChunkIndex = currentChunkIndexRef.current + 1;
      if (nextChunkIndex < chunkPathsRef.current.length) {
        // Play next chunk
        currentChunkIndexRef.current = nextChunkIndex;
        const nextPath = chunkPathsRef.current[nextChunkIndex];

        setCurrentChunk(nextChunkIndex + 1);
        setIsLastChunk(nextChunkIndex + 1 >= chunkPathsRef.current.length);

        player.reset();
        invoke<NativePlayResult>('play_audio_native', { filePath: nextPath }).then(result => {
          player.setDuration(result.duration);
          player.startPlayback();
        }).catch(err => {
          console.error('[AudioContext] Failed to play next chunk:', err);
          setIsPlaying(false);
          resetChunkState();
        });
      } else {
        // All chunks done
        player.markEnded();
        setIsPlaying(false);
        resetChunkState();
      }
    }).then(unlisten => {
      unlistenRef.current = unlisten;
    });

    return () => {
      mounted = false;
      if (unlistenRef.current) {
        unlistenRef.current();
      }
      resetChunkState();
    };
  }, []);

  const playTTS = useCallback(async (userId: string, qubeId: string, text: string, password: string) => {
    if (lastPlayedTextRef.current === text) {
      throw new Error('TTS skipped: duplicate text');
    }

    const player = playerRef.current;
    if (!player) throw new Error('Audio player not initialized');

    try {
      const speechResponse = await invoke<SpeechResponse>('generate_speech', {
        userId,
        qubeId,
        text,
        password
      });

      if (speechResponse.success && speechResponse.audio_path) {
        const numChunks = speechResponse.total_chunks || 1;

        // Build chunk file paths
        const chunkPaths: string[] = [];
        for (let i = 1; i <= numChunks; i++) {
          let chunkFilePath = speechResponse.audio_path;
          if (numChunks > 1) {
            if (chunkFilePath.includes('_chunk_1')) {
              chunkFilePath = chunkFilePath.replace('_chunk_1', `_chunk_${i}`);
            } else {
              const extension = chunkFilePath.substring(chunkFilePath.lastIndexOf('.'));
              const basePath = chunkFilePath.substring(0, chunkFilePath.lastIndexOf('.'));
              chunkFilePath = `${basePath}_chunk_${i}${extension}`;
            }
          }
          chunkPaths.push(chunkFilePath);
        }

        // Set up chunk queue
        chunkPathsRef.current = chunkPaths;
        currentChunkIndexRef.current = 0;

        setTotalChunks(numChunks);
        setCurrentChunk(1);
        setIsLastChunk(numChunks <= 1);

        // Reset and play first chunk
        player.reset();
        await playFileNative(chunkPaths[0]);

        lastPlayedTextRef.current = text;
      } else {
        console.error('[AudioContext] TTS generation failed:', speechResponse.error);
        throw new Error(`TTS generation failed: ${speechResponse.error}`);
      }
    } catch (err) {
      console.error('[AudioContext] TTS error:', err);
      resetChunkState();
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
        return speechResponse.audio_path;
      } else {
        throw new Error(`TTS prefetch failed: ${speechResponse.error}`);
      }
    } catch (err) {
      console.error('TTS prefetch error:', err);
      throw err;
    }
  }, []);

  const playPrefetchedTTS = useCallback(async (audioPath: string, text: string): Promise<void> => {
    if (lastPlayedTextRef.current === text) {
      throw new Error('TTS skipped: duplicate text');
    }

    const player = playerRef.current;
    if (!player) throw new Error('Audio player not initialized');

    try {
      setTotalChunks(1);
      setCurrentChunk(1);
      setIsLastChunk(true);
      chunkPathsRef.current = [audioPath];
      currentChunkIndexRef.current = 0;

      player.reset();
      await playFileNative(audioPath);

      lastPlayedTextRef.current = text;
    } catch (err) {
      console.error('Prefetched TTS playback error:', err);
      throw err;
    }
  }, []);

  const stopAudio = useCallback(() => {
    if (playerRef.current) {
      playerRef.current.stop();
    }
    // Kill native playback process
    invoke('stop_audio_native').catch(() => {});
    setIsPlaying(false);
    resetChunkState();
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
