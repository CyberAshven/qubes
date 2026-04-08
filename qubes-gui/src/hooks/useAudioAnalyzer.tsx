import { useState, useEffect, useRef, useCallback } from 'react';
import { emitTo } from '@tauri-apps/api/event';
import type { AnimationSmoothness } from '../types';
import type { AudioPlaybackElement } from '../contexts/AudioContext';

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
  audioElement: AudioPlaybackElement | null,
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
  const bufferSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const startTimeRef = useRef<number>(0);
  const currentAudioDataRef = useRef<string | null>(null); // Track which data URL we've decoded

  // Calculate target FPS based on smoothness setting
  const getTargetFps = useCallback(() => {
    switch (animationSmoothness) {
      case 'low': return 30;
      case 'medium': return 45;
      case 'high': return 60;
      case 'ultra': return 60;
      default: return 45;
    }
  }, [animationSmoothness]);

  const getFrameInterval = useCallback(() => {
    if (animationSmoothness === 'ultra') return 0;
    return 1000 / getTargetFps();
  }, [animationSmoothness, getTargetFps]);

  // Ensure AudioContext and AnalyserNode exist
  const ensureContext = useCallback(() => {
    if (!audioContextRef.current || audioContextRef.current.state === 'closed') {
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
    }
    if (!analyzerRef.current) {
      const analyzer = audioContextRef.current.createAnalyser();
      analyzer.fftSize = fftSize;
      analyzer.smoothingTimeConstant = 0.6;
      analyzer.minDecibels = -80;
      analyzer.maxDecibels = -10;
      analyzerRef.current = analyzer;
    }
    return { audioContext: audioContextRef.current, analyzer: analyzerRef.current };
  }, [fftSize]);

  // Load audio data and create a silent BufferSource for analysis
  const loadAudioData = useCallback(async (audioDataUrl: string) => {
    if (!audioDataUrl || currentAudioDataRef.current === audioDataUrl) return;
    currentAudioDataRef.current = audioDataUrl;

    try {
      const { audioContext, analyzer } = ensureContext();

      // Stop any existing buffer source
      if (bufferSourceRef.current) {
        try { bufferSourceRef.current.stop(); } catch (_) {}
        bufferSourceRef.current = null;
      }

      // Fetch and decode the audio data
      const response = await fetch(audioDataUrl);
      const arrayBuffer = await response.arrayBuffer();
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

      // Create a BufferSource connected to the analyzer only (no speakers)
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(analyzer);
      // NOT connected to audioContext.destination — silent analysis only

      source.onended = () => {
        bufferSourceRef.current = null;
      };

      bufferSourceRef.current = source;
      source.start(0);
    } catch (err) {
      console.warn('[AudioAnalyzer] Failed to decode audio for visualization:', err);
      currentAudioDataRef.current = null;
    }
  }, [ensureContext]);

  // Start the animation frame loop to read analyzer data
  const startAnalyzing = useCallback(() => {
    if (!analyzerRef.current || isAnalyzing) return;

    setIsAnalyzing(true);
    startTimeRef.current = performance.now();

    const analyze = (timestamp: number) => {
      if (!analyzerRef.current) return;

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

      const frequencyData = new Uint8Array(bufferLength);
      analyzer.getByteFrequencyData(frequencyData);

      const waveformData = new Uint8Array(bufferLength);
      analyzer.getByteTimeDomainData(waveformData);

      // Calculate volume (RMS)
      let sum = 0;
      for (let i = 0; i < waveformData.length; i++) {
        const normalized = (waveformData[i] - 128) / 128;
        sum += normalized * normalized;
      }
      const rms = Math.sqrt(sum / waveformData.length);

      const sensitivityMultiplier = 0.5 + (sensitivity / 100) * 1.5;
      const volume = Math.min(1.0, rms * sensitivityMultiplier);

      // Apply sensitivity and noise filtering to frequency data
      const adjustedFrequencyData = new Uint8Array(bufferLength);
      const noiseFloor = 25;
      const spikeThreshold = 40;

      for (let i = 0; i < bufferLength; i++) {
        if (i < 5) { adjustedFrequencyData[i] = 0; continue; }

        const raw = frequencyData[i];
        if (raw < noiseFloor) { adjustedFrequencyData[i] = 0; continue; }

        const prev = i > 0 ? frequencyData[i - 1] : 0;
        const next = i < bufferLength - 1 ? frequencyData[i + 1] : 0;
        const neighborAvg = (prev + next) / 2;
        if (raw > neighborAvg + spikeThreshold && neighborAvg < noiseFloor) {
          adjustedFrequencyData[i] = 0;
          continue;
        }

        adjustedFrequencyData[i] = Math.min(255, raw * sensitivityMultiplier);
      }

      setAnalyzerData({ frequencyData: adjustedFrequencyData, waveformData, volume });

      emitTo('visualizer', 'visualizer-audio-data', {
        frequencyData: Array.from(adjustedFrequencyData)
      }).catch(() => {});

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
    // Stop buffer source
    if (bufferSourceRef.current) {
      try { bufferSourceRef.current.stop(); } catch (_) {}
      bufferSourceRef.current = null;
    }
    currentAudioDataRef.current = null;
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

  // Handle audio playback state from the NativeAudioPlayer events
  useEffect(() => {
    if (!audioElement) return;

    const handlePlay = () => {
      if (audioOffsetMs !== 0 && audioElement) {
        const offsetSeconds = audioOffsetMs / 1000;
        const newTime = audioElement.currentTime + offsetSeconds;
        if (newTime >= 0 && newTime <= audioElement.duration) {
          audioElement.currentTime = newTime;
        }
      }

      if (audioContextRef.current && audioContextRef.current.state === 'suspended') {
        audioContextRef.current.resume();
      }

      startAnalyzing();
    };

    const handlePause = () => stopAnalyzing();
    const handleEnded = () => stopAnalyzing();

    audioElement.addEventListener('play', handlePlay);
    audioElement.addEventListener('pause', handlePause);
    audioElement.addEventListener('ended', handleEnded);

    if (!audioElement.paused && !audioElement.ended) {
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
    stopAnalyzing,
    loadAudioData,
  };
}
