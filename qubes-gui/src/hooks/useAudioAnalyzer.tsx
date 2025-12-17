import { useState, useEffect, useRef, useCallback } from 'react';
import { emit, emitTo } from '@tauri-apps/api/event';
import type { AnimationSmoothness } from '../types';

interface AudioAnalyzerOptions {
  fftSize?: 256 | 512 | 1024 | 2048 | 4096;
  smoothingTimeConstant?: number;
  sensitivity?: number; // 0-100
  audioOffsetMs?: number; // -500 to +500
  animationSmoothness?: AnimationSmoothness;
}

interface AudioAnalyzerData {
  frequencyData: Uint8Array;
  waveformData: Uint8Array;
  volume: number;
}

export function useAudioAnalyzer(
  audioElement: HTMLAudioElement | null,
  options: AudioAnalyzerOptions = {}
) {
  const {
    fftSize = 2048,
    smoothingTimeConstant = 0.8,
    sensitivity = 50,
    audioOffsetMs = 0,
    animationSmoothness = 'medium'
  } = options;

  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzerData, setAnalyzerData] = useState<AudioAnalyzerData | null>(null);

  const audioContextRef = useRef<AudioContext | null>(null);
  const analyzerRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaElementAudioSourceNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const startTimeRef = useRef<number>(0);

  // Calculate target FPS based on smoothness setting
  const getTargetFps = useCallback(() => {
    switch (animationSmoothness) {
      case 'low': return 30;
      case 'medium': return 45;
      case 'high': return 60;
      case 'ultra': return 60; // Will run uncapped
      default: return 45;
    }
  }, [animationSmoothness]);

  // Calculate frame interval (ms between frames)
  const getFrameInterval = useCallback(() => {
    if (animationSmoothness === 'ultra') return 0; // No throttling
    return 1000 / getTargetFps();
  }, [animationSmoothness, getTargetFps]);

  // Initialize Web Audio API
  const initializeAudioContext = useCallback(() => {
    if (!audioElement) return;

    // Don't re-initialize if already set up
    if (audioContextRef.current && sourceRef.current && analyzerRef.current) {
      return;
    }

    try {
      // Create AudioContext
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      audioContextRef.current = audioContext;

      // Create AnalyserNode
      const analyzer = audioContext.createAnalyser();
      analyzer.fftSize = fftSize;
      analyzer.smoothingTimeConstant = smoothingTimeConstant;
      analyzerRef.current = analyzer;

      // IMPORTANT: Only create MediaElementSource once
      // Check if the audio element already has a source connected
      if (!sourceRef.current) {
        try {
          const source = audioContext.createMediaElementSource(audioElement);
          sourceRef.current = source;

          // Connect: source -> analyzer -> destination
          source.connect(analyzer);
          analyzer.connect(audioContext.destination);

          console.log('Audio analyzer initialized:', {
            fftSize,
            frequencyBinCount: analyzer.frequencyBinCount,
            sampleRate: audioContext.sampleRate
          });
        } catch (error: any) {
          // If we get an error about the element already being used, that's OK
          // It means the audio is already connected elsewhere
          if (error.name === 'InvalidStateError') {
            console.warn('Audio element already connected to a source. Visualizer will not work.');
          } else {
            throw error;
          }
        }
      }
    } catch (error) {
      console.error('Failed to initialize audio analyzer:', error);
    }
  }, [audioElement, fftSize, smoothingTimeConstant]);

  // Start analyzing
  const startAnalyzing = useCallback(() => {
    if (!analyzerRef.current || isAnalyzing) return;

    setIsAnalyzing(true);
    startTimeRef.current = performance.now();

    const analyze = (timestamp: number) => {
      if (!analyzerRef.current) return;

      // Throttle based on animation smoothness
      const frameInterval = getFrameInterval();
      if (frameInterval > 0) {
        const elapsed = timestamp - startTimeRef.current;
        if (elapsed < frameInterval) {
          animationFrameRef.current = requestAnimationFrame(analyze);
          return;
        }
        startTimeRef.current = timestamp;
      }

      const analyzer = analyzerRef.current;
      const bufferLength = analyzer.frequencyBinCount;

      // Get frequency data (0-255 for each frequency bin)
      const frequencyData = new Uint8Array(bufferLength);
      analyzer.getByteFrequencyData(frequencyData);

      // Get waveform data (time domain)
      const waveformData = new Uint8Array(bufferLength);
      analyzer.getByteTimeDomainData(waveformData);

      // Calculate volume (RMS of waveform)
      let sum = 0;
      for (let i = 0; i < waveformData.length; i++) {
        const normalized = (waveformData[i] - 128) / 128;
        sum += normalized * normalized;
      }
      const rms = Math.sqrt(sum / waveformData.length);

      // Apply sensitivity multiplier (0-100 -> 0.5-2.0)
      const sensitivityMultiplier = 0.5 + (sensitivity / 100) * 1.5;
      const volume = Math.min(1.0, rms * sensitivityMultiplier);

      // Apply sensitivity to frequency data
      const adjustedFrequencyData = new Uint8Array(bufferLength);
      for (let i = 0; i < bufferLength; i++) {
        adjustedFrequencyData[i] = Math.min(255, frequencyData[i] * sensitivityMultiplier);
      }

      setAnalyzerData({
        frequencyData: adjustedFrequencyData,
        waveformData,
        volume
      });

      // Broadcast frequency data to visualizer window via Tauri events
      // Convert Uint8Array to regular array for serialization
      // Use emitTo to target the specific visualizer window
      emitTo('visualizer', 'visualizer-audio-data', {
        frequencyData: Array.from(adjustedFrequencyData)
      }).then(() => {
        // Success - only log first few
        if (performance.now() - startTimeRef.current < 1000) {
          console.log('🎵 Main window: Emitted audio data to visualizer window');
        }
      }).catch(err => {
        // If visualizer window doesn't exist, silently fail
        if (performance.now() - startTimeRef.current < 1000) {
          console.log('🎵 Main window: Visualizer window not found (this is OK if using overlay)');
        }
      });

      animationFrameRef.current = requestAnimationFrame(analyze);
    };

    animationFrameRef.current = requestAnimationFrame(analyze);
  }, [isAnalyzing, sensitivity, getFrameInterval]);

  // Stop analyzing
  const stopAnalyzing = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    setIsAnalyzing(false);
    setAnalyzerData(null);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopAnalyzing();
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close();
      }
    };
  }, [stopAnalyzing]);

  // Initialize when audio element is available
  useEffect(() => {
    if (audioElement && !audioContextRef.current) {
      initializeAudioContext();
    }
  }, [audioElement, initializeAudioContext]);

  // Handle audio playback state
  useEffect(() => {
    if (!audioElement) return;

    const handlePlay = () => {
      // Apply audio offset for Bluetooth sync
      if (audioOffsetMs !== 0 && audioElement) {
        const offsetSeconds = audioOffsetMs / 1000;
        const newTime = audioElement.currentTime + offsetSeconds;
        if (newTime >= 0 && newTime <= audioElement.duration) {
          audioElement.currentTime = newTime;
        }
      }

      // Resume AudioContext if suspended
      if (audioContextRef.current && audioContextRef.current.state === 'suspended') {
        audioContextRef.current.resume();
      }

      startAnalyzing();
    };

    const handlePause = () => {
      stopAnalyzing();
    };

    const handleEnded = () => {
      stopAnalyzing();
    };

    audioElement.addEventListener('play', handlePlay);
    audioElement.addEventListener('pause', handlePause);
    audioElement.addEventListener('ended', handleEnded);

    // If audio is already playing when this hook initializes, start analyzing immediately
    // This handles the case where the visualizer is toggled on mid-playback
    if (!audioElement.paused && !audioElement.ended) {
      console.log('🎵 Audio already playing, starting analyzer immediately');
      startAnalyzing();
    }

    return () => {
      audioElement.removeEventListener('play', handlePlay);
      audioElement.removeEventListener('pause', handlePause);
      audioElement.removeEventListener('ended', handleEnded);
    };
  }, [audioElement, audioOffsetMs, startAnalyzing, stopAnalyzing]);

  return {
    isAnalyzing,
    analyzerData,
    audioContext: audioContextRef.current,
    startAnalyzing,
    stopAnalyzing
  };
}
