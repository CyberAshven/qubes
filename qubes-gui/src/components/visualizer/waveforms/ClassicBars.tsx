import React, { useEffect, useRef } from 'react';

interface ClassicBarsProps {
  frequencyData: Uint8Array;
  colors: string | string[];
  width: number;
  height: number;
  frequencyRange: number;
}

export const ClassicBars: React.FC<ClassicBarsProps> = ({
  frequencyData,
  colors,
  width,
  height,
  frequencyRange
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(0);
  const scanLineRef = useRef<number>(0);
  const peaksRef = useRef<number[]>([]);

  const getColor = () => {
    if (Array.isArray(colors) && colors.length > 0) return colors[0];
    return typeof colors === 'string' ? colors : '#00ffff';
  };

  const parseHex = (hex: string) => {
    const h = hex.replace('#', '');
    return {
      r: parseInt(h.substr(0, 2), 16),
      g: parseInt(h.substr(2, 2), 16),
      b: parseInt(h.substr(4, 2), 16)
    };
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = width;
    canvas.height = height;

    const primaryColor = getColor();
    const rgb = parseHex(primaryColor);
    const barCount = 64;

    // Initialize peaks
    if (peaksRef.current.length !== barCount) {
      peaksRef.current = new Array(barCount).fill(0);
    }

    const animate = () => {
      scanLineRef.current = (scanLineRef.current + 1.5) % height;

      // Dark gradient background
      const bgGrad = ctx.createLinearGradient(0, 0, 0, height);
      bgGrad.addColorStop(0, '#0a0a12');
      bgGrad.addColorStop(1, '#050508');
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, width, height);

      // Grid
      ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.07)`;
      ctx.lineWidth = 1;
      const gridSize = 30;
      for (let x = 0; x < width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Scan line
      const scanGrad = ctx.createLinearGradient(0, scanLineRef.current - 30, 0, scanLineRef.current + 30);
      scanGrad.addColorStop(0, 'transparent');
      scanGrad.addColorStop(0.5, `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.1)`);
      scanGrad.addColorStop(1, 'transparent');
      ctx.fillStyle = scanGrad;
      ctx.fillRect(0, scanLineRef.current - 30, width, 60);

      const usableDataLength = Math.floor(frequencyData.length * (frequencyRange / 100));
      const barWidth = width / barCount;
      const gap = Math.max(2, barWidth * 0.2);
      const actualBarWidth = barWidth - gap;
      const peaks = peaksRef.current;

      for (let i = 0; i < barCount; i++) {
        const dataIndex = Math.floor((i / barCount) * usableDataLength);
        // Skip first 2 bins (DC offset)
        const value = dataIndex < 2 ? 0 : frequencyData[dataIndex];
        const normalizedValue = value / 255;

        // Threshold
        if (normalizedValue < 0.03) {
          // Decay peak
          peaks[i] = Math.max(0, peaks[i] - 0.02);
          continue;
        }

        const barHeight = normalizedValue * (height - 40);
        const x = i * barWidth + gap / 2;
        const y = height - barHeight - 20;

        // Update peak
        if (normalizedValue > peaks[i]) {
          peaks[i] = normalizedValue;
        } else {
          peaks[i] = Math.max(0, peaks[i] - 0.01);
        }

        // Color based on intensity
        let r = rgb.r, g = rgb.g, b = rgb.b;
        if (normalizedValue > 0.7) {
          r = Math.min(255, rgb.r + 100);
          g = Math.min(255, rgb.g - 50);
          b = Math.max(0, rgb.b - 100);
        }

        // Bar glow
        for (let glow = 3; glow >= 0; glow--) {
          const alpha = (0.15 - glow * 0.04) * normalizedValue;
          ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
          ctx.fillRect(x - glow * 3, y - glow * 3, actualBarWidth + glow * 6, barHeight + glow * 6);
        }

        // Main bar gradient
        const barGrad = ctx.createLinearGradient(x, y + barHeight, x, y);
        barGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.9)`);
        barGrad.addColorStop(0.5, `rgba(${Math.min(255, r + 50)}, ${Math.min(255, g + 50)}, ${Math.min(255, b + 50)}, 1)`);
        barGrad.addColorStop(1, `rgba(255, 255, 255, 0.9)`);
        ctx.fillStyle = barGrad;
        ctx.fillRect(x, y, actualBarWidth, barHeight);

        // Peak indicator
        if (peaks[i] > 0.05) {
          const peakY = height - peaks[i] * (height - 40) - 20;
          ctx.fillStyle = '#ffffff';
          ctx.shadowColor = primaryColor;
          ctx.shadowBlur = 10;
          ctx.fillRect(x, peakY - 3, actualBarWidth, 3);
          ctx.shadowBlur = 0;
        }
      }

      // Corner brackets
      ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.5)`;
      ctx.lineWidth = 2;
      const cs = 25;
      ctx.beginPath();
      ctx.moveTo(15, 15 + cs); ctx.lineTo(15, 15); ctx.lineTo(15 + cs, 15);
      ctx.moveTo(width - 15 - cs, 15); ctx.lineTo(width - 15, 15); ctx.lineTo(width - 15, 15 + cs);
      ctx.moveTo(15, height - 15 - cs); ctx.lineTo(15, height - 15); ctx.lineTo(15 + cs, height - 15);
      ctx.moveTo(width - 15 - cs, height - 15); ctx.lineTo(width - 15, height - 15); ctx.lineTo(width - 15, height - 15 - cs);
      ctx.stroke();

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();
    return () => cancelAnimationFrame(animationRef.current);
  }, [frequencyData, colors, width, height, frequencyRange]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      style={{ position: 'absolute', top: 0, left: 0 }}
    />
  );
};
