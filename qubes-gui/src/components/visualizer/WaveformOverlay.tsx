import React, { useEffect, useState, useCallback } from 'react';
import { useAudioAnalyzer } from '../../hooks/useAudioAnalyzer';
import type { WaveformStyle, ColorTheme, GradientStyle, AnimationSmoothness } from '../../types';
import { ClassicBars } from './waveforms/ClassicBars';
import { SymmetricBars } from './waveforms/SymmetricBars';
import { SmoothWaveform } from './waveforms/SmoothWaveform';
import { RadialSpectrum } from './waveforms/RadialSpectrum';
import { DotMatrix } from './waveforms/DotMatrix';
import { PolygonMorph } from './waveforms/PolygonMorph';
import { ConcentricCircles } from './waveforms/ConcentricCircles';
import { SpiralWave } from './waveforms/SpiralWave';
import { ParticleField } from './waveforms/ParticleField';
import { RingBars } from './waveforms/RingBars';
import { WaveMesh } from './waveforms/WaveMesh';

interface WaveformOverlayProps {
  audioElement: HTMLAudioElement | null;
  isPlaying: boolean;
  qubeFavoriteColor: string;
  waveformStyle: WaveformStyle;
  colorTheme: ColorTheme;
  gradientStyle: GradientStyle;
  sensitivity: number;
  animationSmoothness: AnimationSmoothness;
  audioOffsetMs: number;
  frequencyRange: number;
  enabled: boolean;
  outputMonitor: number;
  onWaveformChange?: (style: WaveformStyle) => void;
  onToggle?: (enabled: boolean) => void;
}

export const WaveformOverlay: React.FC<WaveformOverlayProps> = ({
  audioElement,
  isPlaying,
  qubeFavoriteColor,
  waveformStyle,
  colorTheme,
  gradientStyle,
  sensitivity,
  animationSmoothness,
  audioOffsetMs,
  frequencyRange,
  enabled,
  outputMonitor,
  onWaveformChange,
  onToggle
}) => {
  const [visible, setVisible] = useState(false);
  const [currentWaveform, setCurrentWaveform] = useState<WaveformStyle>(waveformStyle);

  // Initialize audio analyzer when audio is playing (always ready for V key toggle)
  // The 'enabled' flag just controls whether we display the visualization
  const { isAnalyzing, analyzerData } = useAudioAnalyzer(
    isPlaying ? audioElement : null,
    {
      fftSize: 2048,
      smoothingTimeConstant: 0.8,
      sensitivity,
      audioOffsetMs,
      animationSmoothness
    }
  );

  // Show/hide overlay based on playback state and enabled setting
  // Hide overlay when external monitor is selected (outputMonitor > 0)
  useEffect(() => {
    setVisible(isPlaying && enabled && isAnalyzing && outputMonitor === 0);
  }, [isPlaying, enabled, isAnalyzing, outputMonitor]);

  // Sync waveform style prop with internal state
  useEffect(() => {
    setCurrentWaveform(waveformStyle);
  }, [waveformStyle]);

  // Keyboard shortcuts (1-9, 0, -, and V)
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    // Only handle shortcuts if not typing in an input field
    const target = event.target as HTMLElement;
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
      return;
    }

    // 1-9: Waveforms 1-9
    if (event.key >= '1' && event.key <= '9') {
      event.preventDefault();
      const newStyle = parseInt(event.key) as WaveformStyle;
      setCurrentWaveform(newStyle);
      onWaveformChange?.(newStyle);
    }
    // 0: Waveform 10
    else if (event.key === '0') {
      event.preventDefault();
      setCurrentWaveform(10);
      onWaveformChange?.(10);
    }
    // -: Waveform 11
    else if (event.key === '-' || event.key === '_') {
      event.preventDefault();
      setCurrentWaveform(11);
      onWaveformChange?.(11);
    }
    // V: Toggle visualizer on/off
    else if (event.key === 'v' || event.key === 'V') {
      event.preventDefault();
      const newEnabled = !enabled;
      onToggle?.(newEnabled);
    }
  }, [enabled, onWaveformChange, onToggle]);

  // Register keyboard event listener
  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown]);

  // Get color based on theme and qube color
  const getColor = useCallback((): string | string[] => {
    switch (colorTheme) {
      case 'qube-color':
        if (gradientStyle === 'solid') {
          return qubeFavoriteColor;
        } else if (gradientStyle === 'gradient-dark') {
          return [qubeFavoriteColor, '#000000'];
        } else if (gradientStyle === 'gradient-complementary') {
          // Calculate complementary color (opposite on color wheel)
          const hex = qubeFavoriteColor.replace('#', '');
          const r = parseInt(hex.substr(0, 2), 16);
          const g = parseInt(hex.substr(2, 2), 16);
          const b = parseInt(hex.substr(4, 2), 16);
          const compR = 255 - r;
          const compG = 255 - g;
          const compB = 255 - b;
          const complementary = `#${compR.toString(16).padStart(2, '0')}${compG.toString(16).padStart(2, '0')}${compB.toString(16).padStart(2, '0')}`;
          return [qubeFavoriteColor, complementary];
        }
        return qubeFavoriteColor;
      case 'rainbow':
        return ['#ff0000', '#ff7f00', '#ffff00', '#00ff00', '#0000ff', '#4b0082', '#9400d3'];
      case 'neon-cyan':
        return ['#00ffff', '#00ccff'];
      case 'electric-purple':
        return ['#bf00ff', '#ff00ff'];
      case 'matrix-green':
        return ['#00ff00', '#003300'];
      case 'fire':
        return ['#ff0000', '#ff7700', '#ffff00'];
      case 'ice':
        return ['#00ffff', '#0088ff', '#ffffff'];
      default:
        return qubeFavoriteColor;
    }
  }, [colorTheme, qubeFavoriteColor, gradientStyle]);

  // Render appropriate waveform component
  const renderWaveform = () => {
    if (!analyzerData) return null;

    const colors = getColor();

    switch (currentWaveform) {
      case 1: // Classic Bars
        return (
          <ClassicBars
            frequencyData={analyzerData.frequencyData}
            colors={colors}
            width={window.innerWidth}
            height={window.innerHeight}
            frequencyRange={frequencyRange}
          />
        );
      case 2: // Symmetric Bars
        return (
          <SymmetricBars
            frequencyData={analyzerData.frequencyData}
            colors={colors}
            width={window.innerWidth}
            height={window.innerHeight}
            frequencyRange={frequencyRange}
          />
        );
      case 3: // Smooth Waveform
        return (
          <SmoothWaveform
            frequencyData={analyzerData.frequencyData}
            colors={colors}
            width={window.innerWidth}
            height={window.innerHeight}
            frequencyRange={frequencyRange}
          />
        );
      case 4: // Radial Spectrum
        return (
          <RadialSpectrum
            frequencyData={analyzerData.frequencyData}
            colors={colors}
            width={window.innerWidth}
            height={window.innerHeight}
            frequencyRange={frequencyRange}
          />
        );
      case 5: // Dot Matrix
        return (
          <DotMatrix
            frequencyData={analyzerData.frequencyData}
            colors={colors}
            width={window.innerWidth}
            height={window.innerHeight}
            frequencyRange={frequencyRange}
          />
        );
      case 6: // Polygon Morph
        return (
          <PolygonMorph
            frequencyData={analyzerData.frequencyData}
            colors={colors}
            width={window.innerWidth}
            height={window.innerHeight}
            frequencyRange={frequencyRange}
          />
        );
      case 7: // Concentric Circles
        return (
          <ConcentricCircles
            frequencyData={analyzerData.frequencyData}
            colors={colors}
            width={window.innerWidth}
            height={window.innerHeight}
            frequencyRange={frequencyRange}
          />
        );
      case 8: // Spiral Wave
        return (
          <SpiralWave
            frequencyData={analyzerData.frequencyData}
            colors={colors}
            width={window.innerWidth}
            height={window.innerHeight}
            frequencyRange={frequencyRange}
          />
        );
      case 9: // Particle Field
        return (
          <ParticleField
            frequencyData={analyzerData.frequencyData}
            colors={colors}
            width={window.innerWidth}
            height={window.innerHeight}
            frequencyRange={frequencyRange}
          />
        );
      case 10: // Ring Bars
        return (
          <RingBars
            frequencyData={analyzerData.frequencyData}
            colors={colors}
            width={window.innerWidth}
            height={window.innerHeight}
            frequencyRange={frequencyRange}
          />
        );
      case 11: // Wave Mesh
        return (
          <WaveMesh
            frequencyData={analyzerData.frequencyData}
            colors={colors}
            width={window.innerWidth}
            height={window.innerHeight}
            frequencyRange={frequencyRange}
          />
        );
      default:
        return null;
    }
  };

  if (!visible) return null;

  return (
    <div
      className="fixed inset-0 z-[9999] bg-black"
      style={{
        opacity: 1,
        pointerEvents: 'none' // Allow clicks to pass through
      }}
    >
      <div className="relative w-full h-full">
        {renderWaveform()}

        {/* Keyboard hint */}
        <div className="absolute bottom-4 right-4 text-white/30 text-xs font-mono pointer-events-none">
          1-9, 0, -: Switch Style | V: Toggle
        </div>
      </div>
    </div>
  );
};
