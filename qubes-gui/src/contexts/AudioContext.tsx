import React, { createContext, useContext, useRef, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen, type UnlistenFn } from '@tauri-apps/api/event';

// Minimal interface matching the HTMLAudioElement properties that TypewriterText uses.
// Implemented by NativeAudioPlayer (all platforms via Rust native audio playback).
export interface AudioPlaybackElement {
  currentTime: number;
  readonly duration: number;
  readonly paused: boolean;
  readonly ended: boolean;
  readonly readyState: number;
  readonly error: { code: number; message: string } | null;
  src: string;
  addEventListener(event: string, handler: EventListenerOrEventListenerObject): void;
  removeEventListener(event: string, handler: EventListenerOrEventListenerObject): void;
  pause(): void;
  load(): void;
  removeAttribute(name: string): void;
}

interface AudioContextType {
  playTTS: (userId: string, qubeId: string, text: string, password: string) => Promise<void>;
  prefetchTTS: (userId: string, qubeId: string, text: string, password: string) => Promise<string>;
  playPrefetchedTTS: (blobUrl: string, text: string) => Promise<void>;
  stopAudio: () => void;
  startStreamingPlayback: () => void;
  resetStreamingState: () => void;
  isPlaying: boolean;
  audioElement: AudioPlaybackElement | null;
  audioDataUrl: string | null;
  currentSentence: string | null;
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

  // AudioPlaybackElement interface methods
  pause(): void { this.stop(); }
  load(): void { this.reset(); }
  removeAttribute(_name: string): void {
    if (_name === 'src') this.src = '';
  }

  set currentTime(value: number) {
    // Timer-based player doesn't support seeking; ignore assignment
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
  const [audioDataUrl, setAudioDataUrl] = React.useState<string | null>(null);
  const lastPlayedTextRef = useRef<string>('');
  const unlistenRef = useRef<UnlistenFn | null>(null);

  // Multi-chunk playback state
  const chunkPathsRef = useRef<string[]>([]);
  const currentChunkIndexRef = useRef<number>(0);
  const playbackTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [totalChunks, setTotalChunks] = React.useState(1);
  const [currentChunk, setCurrentChunk] = React.useState(1);
  const [isLastChunk, setIsLastChunk] = React.useState(true);

  // Streaming TTS: ordered chunk map guarantees playback order
  const streamingChunkMap = useRef<Map<number, string | null>>(new Map());
  const streamingSentenceMap = useRef<Map<number, string>>(new Map());  // chunk_index → sentence text
  const nextExpectedChunk = useRef(1);
  const isStreamingActive = useRef(false);
  const streamingDone = useRef(false);
  const isPlayingChunk = useRef(false);  // Guard against concurrent playback
  // Current sentence being spoken (for text-audio sync)
  const [currentSentence, setCurrentSentence] = React.useState<string | null>(null);

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

  const resetStreamingState = useCallback(() => {
    streamingChunkMap.current.clear();
    streamingSentenceMap.current.clear();
    nextExpectedChunk.current = 1;
    isStreamingActive.current = false;
    streamingDone.current = false;
    isPlayingChunk.current = false;
    setCurrentSentence(null);
  }, []);

  const startStreamingPlayback = useCallback(() => {
    resetStreamingState();
    isStreamingActive.current = true;
  }, [resetStreamingState]);

  const playNextStreamingChunk = useCallback(async () => {
    // Guard: prevent concurrent playback
    if (isPlayingChunk.current) return;

    const chunkIndex = nextExpectedChunk.current;
    const path = streamingChunkMap.current.get(chunkIndex);

    if (path === undefined) {
      // Chunk not arrived yet
      if (streamingDone.current) {
        setIsPlaying(false);
        isPlayingChunk.current = false;
        resetStreamingState();
      }
      // Otherwise, wait — tts-audio-ready listener will call us
      return;
    }

    // Advance past this chunk
    nextExpectedChunk.current = chunkIndex + 1;
    streamingChunkMap.current.delete(chunkIndex);

    if (path === null) {
      // Error/skipped chunk — advance to next
      playNextStreamingChunk();
      return;
    }

    isPlayingChunk.current = true;

    try {
      // Set the sentence being spoken (for text-audio sync in ChatInterface)
      const sentence = streamingSentenceMap.current.get(chunkIndex) || null;
      setCurrentSentence(sentence);
      streamingSentenceMap.current.delete(chunkIndex);

      setIsPlaying(true);
      const player = playerRef.current;
      if (!player) return;
      player.reset();
      const result = await invoke<NativePlayResult>('play_audio_native', { filePath: path });
      player.setDuration(result.duration);
      player.startPlayback();
      startPlaybackTimeout(result.duration);
      // Load audio data for visualizer (fire-and-forget, doesn't block playback)
      invoke<string>('get_audio_base64', { filePath: path }).then(setAudioDataUrl).catch(() => {});
    } catch (err) {
      console.error('[AudioContext] Streaming chunk playback failed:', err);
      isPlayingChunk.current = false;
      playNextStreamingChunk();
    }
  }, [resetStreamingState]);

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
    // Load audio data for visualizer (fire-and-forget)
    invoke<string>('get_audio_base64', { filePath }).then(setAudioDataUrl).catch(() => {});
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
    listen<{ success: boolean; error?: string }>('audio-playback-ended', (event) => {
      if (!mounted) return;
      clearPlaybackTimeout();

      // Log playback errors (player not found, exit error, etc.)
      if (event.payload && !event.payload.success && event.payload.error) {
        console.error('[AudioContext] Playback failed:', event.payload.error);
      }

      const player = playerRef.current;
      if (!player) return;

      // Streaming mode: play next from ordered chunk map
      if (isStreamingActive.current || streamingChunkMap.current.size > 0) {
        isPlayingChunk.current = false;  // Previous chunk done — allow next
        playNextStreamingChunk();
        return;
      }

      // Non-streaming mode: existing sequential chunk logic
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
          // Load audio data for visualizer (fire-and-forget)
          invoke<string>('get_audio_base64', { filePath: nextPath }).then(setAudioDataUrl).catch(() => {});
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

    // Listen for streaming TTS audio chunks
    let unlistenAudioReady: UnlistenFn | null = null;
    listen<{
      qube_id: string;
      audio_path?: string;
      chunk_index: number;
      is_final: boolean;
      error?: boolean;
      sentence_text?: string;
    }>('tts-audio-ready', (event) => {
      if (!mounted) return;
      const { audio_path, chunk_index, is_final, error, sentence_text } = event.payload;

      streamingChunkMap.current.set(
        chunk_index,
        error ? null : (audio_path ?? null)
      );

      // Store sentence text for audio-synced text reveal
      if (sentence_text) {
        streamingSentenceMap.current.set(chunk_index, sentence_text);
      }

      if (is_final) {
        streamingDone.current = true;
      }

      // If we're waiting for this chunk, start/resume playback
      if (chunk_index === nextExpectedChunk.current) {
        playNextStreamingChunk();
      }
    }).then(u => { unlistenAudioReady = u; });

    // Listen for stream-end
    let unlistenStreamEnd: UnlistenFn | null = null;
    listen<{
      qube_id: string;
      total_chunks: number;
      full_text: string;
    }>('tts-stream-end', (event) => {
      if (!mounted) return;
      streamingDone.current = true;
      // If nothing is playing and queue is empty, clean up
      if (streamingChunkMap.current.size === 0 && !isStreamingActive.current) {
        resetStreamingState();
      }
    }).then(u => { unlistenStreamEnd = u; });

    return () => {
      mounted = false;
      if (unlistenRef.current) {
        unlistenRef.current();
      }
      if (unlistenAudioReady) unlistenAudioReady();
      if (unlistenStreamEnd) unlistenStreamEnd();
      resetChunkState();
      resetStreamingState();
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
    startStreamingPlayback,
    resetStreamingState,
    isPlaying,
    audioElement,
    audioDataUrl,
    currentSentence,
    totalChunks,
    currentChunk,
    isLastChunk,
  };

  return <AudioContext.Provider value={value}>{children}</AudioContext.Provider>;
};
