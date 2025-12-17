import React, { useEffect, useState, useRef, useCallback } from 'react';
import { listen, emit, emitTo } from '@tauri-apps/api/event';
import { invoke } from '@tauri-apps/api/core';
import type { WaveformStyle, ColorTheme, GradientStyle, AnimationSmoothness } from '../types';
import { ClassicBars } from '../components/visualizer/waveforms/ClassicBars';
import { SymmetricBars } from '../components/visualizer/waveforms/SymmetricBars';
import { SmoothWaveform } from '../components/visualizer/waveforms/SmoothWaveform';
import { RadialSpectrum } from '../components/visualizer/waveforms/RadialSpectrum';
import { DotMatrix } from '../components/visualizer/waveforms/DotMatrix';
import { PolygonMorph } from '../components/visualizer/waveforms/PolygonMorph';
import { ConcentricCircles } from '../components/visualizer/waveforms/ConcentricCircles';
import { SpiralWave } from '../components/visualizer/waveforms/SpiralWave';
import { ParticleField } from '../components/visualizer/waveforms/ParticleField';
import { RingBars } from '../components/visualizer/waveforms/RingBars';
import { WaveMesh } from '../components/visualizer/waveforms/WaveMesh';

// This component is displayed in a separate fullscreen window
// It receives visualizer settings and audio data via Tauri events from the main window
export const VisualizerWindow: React.FC = () => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [frequencyData, setFrequencyData] = useState<Uint8Array>(new Uint8Array(1024));
  const [settings, setSettings] = useState({
    waveform_style: 1 as WaveformStyle,
    color_theme: 'qube-color' as ColorTheme,
    gradient_style: 'gradient-dark' as GradientStyle,
    sensitivity: 50,
    animation_smoothness: 'medium' as AnimationSmoothness,
    audio_offset_ms: 0,
    frequency_range: 20,
    qube_favorite_color: '#00ff88'
  });
  const [dataReceivedCount, setDataReceivedCount] = useState(0);
  const [dimensions, setDimensions] = useState({ width: window.innerWidth, height: window.innerHeight });

  // Update dimensions on window resize (handles DPI scaling properly)
  useEffect(() => {
    const handleResize = () => {
      setDimensions({ width: window.innerWidth, height: window.innerHeight });
    };

    window.addEventListener('resize', handleResize);
    // Set initial size
    handleResize();

    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Keyboard handler for waveform switching and closing
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // 1-9: Waveforms 1-9
      if (event.key >= '1' && event.key <= '9') {
        event.preventDefault();
        const newStyle = parseInt(event.key) as WaveformStyle;
        setSettings({ ...settings, waveform_style: newStyle });
      }
      // 0: Waveform 10
      else if (event.key === '0') {
        event.preventDefault();
        setSettings({ ...settings, waveform_style: 10 });
      }
      // -: Waveform 11
      else if (event.key === '-' || event.key === '_') {
        event.preventDefault();
        setSettings({ ...settings, waveform_style: 11 });
      }
      // V: Toggle visualizer (emit event to main window to toggle enabled setting)
      else if (event.key === 'v' || event.key === 'V') {
        event.preventDefault();
        // Emit event to main window to toggle the visualizer enabled setting
        // This will cause the main window to close this window via the lifecycle effect
        emit('visualizer-toggle-request').catch(err => {
          console.error('Failed to emit toggle request:', err);
        });
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [settings]);

  // Listen for Tauri events from main window
  useEffect(() => {
    const setupListeners = async () => {
      // Listen for settings updates
      const unlisten1 = await listen('visualizer-settings-update', (event: any) => {
        setSettings(event.payload);
      });

      // Listen for playback state updates
      const unlisten2 = await listen('visualizer-playback-update', (event: any) => {
        setIsPlaying(event.payload.isPlaying);
      });

      // Listen for audio analyzer data
      const unlisten3 = await listen('visualizer-audio-data', (event: any) => {
        // event.payload.frequencyData is an array, convert to Uint8Array
        const newData = new Uint8Array(event.payload.frequencyData);
        setFrequencyData(newData);
        setDataReceivedCount(prev => prev + 1);
      });

      return () => {
        unlisten1();
        unlisten2();
        unlisten3();
      };
    };

    setupListeners();
  }, [dataReceivedCount]);

  // Helper function to convert RGB to HSL
  const rgbToHsl = (r: number, g: number, b: number): [number, number, number] => {
    r /= 255;
    g /= 255;
    b /= 255;
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    let h = 0, s = 0, l = (max + min) / 2;

    if (max !== min) {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      switch (max) {
        case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
        case g: h = ((b - r) / d + 2) / 6; break;
        case b: h = ((r - g) / d + 4) / 6; break;
      }
    }
    return [h * 360, s * 100, l * 100];
  };

  // Helper function to convert HSL to RGB
  const hslToRgb = (h: number, s: number, l: number): string => {
    h /= 360;
    s /= 100;
    l /= 100;
    let r, g, b;

    if (s === 0) {
      r = g = b = l;
    } else {
      const hue2rgb = (p: number, q: number, t: number) => {
        if (t < 0) t += 1;
        if (t > 1) t -= 1;
        if (t < 1/6) return p + (q - p) * 6 * t;
        if (t < 1/2) return q;
        if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
        return p;
      };
      const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
      const p = 2 * l - q;
      r = hue2rgb(p, q, h + 1/3);
      g = hue2rgb(p, q, h);
      b = hue2rgb(p, q, h - 1/3);
    }
    return `#${Math.round(r * 255).toString(16).padStart(2, '0')}${Math.round(g * 255).toString(16).padStart(2, '0')}${Math.round(b * 255).toString(16).padStart(2, '0')}`;
  };

  // Get color based on theme and qube color
  const getColor = useCallback((): string | string[] => {
    const { color_theme, gradient_style, qube_favorite_color } = settings;

    switch (color_theme) {
      case 'qube-color':
        if (gradient_style === 'solid') {
          return qube_favorite_color;
        } else if (gradient_style === 'gradient-dark') {
          return [qube_favorite_color, '#000000'];
        } else if (gradient_style === 'gradient-complementary') {
          const hex = qube_favorite_color.replace('#', '');
          const r = parseInt(hex.substr(0, 2), 16);
          const g = parseInt(hex.substr(2, 2), 16);
          const b = parseInt(hex.substr(4, 2), 16);
          const compR = 255 - r;
          const compG = 255 - g;
          const compB = 255 - b;
          const complementary = `#${compR.toString(16).padStart(2, '0')}${compG.toString(16).padStart(2, '0')}${compB.toString(16).padStart(2, '0')}`;
          return [qube_favorite_color, complementary];
        } else if (gradient_style === 'gradient-analogous') {
          // Create analogous colors by shifting hue ±30 degrees
          const hex = qube_favorite_color.replace('#', '');
          const r = parseInt(hex.substr(0, 2), 16);
          const g = parseInt(hex.substr(2, 2), 16);
          const b = parseInt(hex.substr(4, 2), 16);
          const [h, s, l] = rgbToHsl(r, g, b);

          const analogous1 = hslToRgb((h + 30) % 360, s, l);
          const analogous2 = hslToRgb((h - 30 + 360) % 360, s, l);
          return [analogous1, qube_favorite_color, analogous2];
        }
        return qube_favorite_color;
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
        return qube_favorite_color;
    }
  }, [settings]);

  // Render appropriate waveform component
  const renderWaveform = useCallback(() => {
    if (!isPlaying) return null;

    try {
      const colors = getColor();
      const { width, height } = dimensions;

      switch (settings.waveform_style) {
        case 1:
          return <ClassicBars frequencyData={frequencyData} colors={colors} width={width} height={height} frequencyRange={settings.frequency_range} />;
        case 2:
          return <SymmetricBars frequencyData={frequencyData} colors={colors} width={width} height={height} frequencyRange={settings.frequency_range} />;
        case 3:
          return <SmoothWaveform frequencyData={frequencyData} colors={colors} width={width} height={height} frequencyRange={settings.frequency_range} />;
        case 4:
          return <RadialSpectrum frequencyData={frequencyData} colors={colors} width={width} height={height} frequencyRange={settings.frequency_range} />;
        case 5:
          return <DotMatrix frequencyData={frequencyData} colors={colors} width={width} height={height} frequencyRange={settings.frequency_range} />;
        case 6:
          return <PolygonMorph frequencyData={frequencyData} colors={colors} width={width} height={height} frequencyRange={settings.frequency_range} />;
        case 7:
          return <ConcentricCircles frequencyData={frequencyData} colors={colors} width={width} height={height} frequencyRange={settings.frequency_range} />;
        case 8:
          return <SpiralWave frequencyData={frequencyData} colors={colors} width={width} height={height} frequencyRange={settings.frequency_range} />;
        case 9:
          return <ParticleField frequencyData={frequencyData} colors={colors} width={width} height={height} frequencyRange={settings.frequency_range} />;
        case 10:
          return <RingBars frequencyData={frequencyData} colors={colors} width={width} height={height} frequencyRange={settings.frequency_range} />;
        case 11:
          return <WaveMesh frequencyData={frequencyData} colors={colors} width={width} height={height} frequencyRange={settings.frequency_range} />;
        default:
          return <ClassicBars frequencyData={frequencyData} colors={colors} width={width} height={height} frequencyRange={settings.frequency_range} />;
      }
    } catch (error) {
      console.error('🎵 VisualizerWindow: Error rendering waveform:', error);
      return <div className="text-white p-4">Error rendering waveform: {String(error)}</div>;
    }
  }, [isPlaying, frequencyData, settings, getColor, dimensions]);

  return (
    <div
      className="bg-black"
      style={{
        width: `${dimensions.width}px`,
        height: `${dimensions.height}px`,
        overflow: 'hidden',
        position: 'fixed',
        top: 0,
        left: 0,
        margin: 0,
        padding: 0
      }}
    >
      {/* Render waveform */}
      {renderWaveform()}
    </div>
  );
};
