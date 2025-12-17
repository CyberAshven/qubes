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

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas resolution - don't use DPR scaling, just use actual dimensions
    canvas.width = width;
    canvas.height = height;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Calculate bar dimensions - use a good number of bars for visual effect
    const barCount = 128; // Fixed number of bars for consistent look
    const barWidth = width / barCount;
    const gap = Math.max(2, barWidth * 0.1); // At least 2px gap, or 10% of bar width
    const actualBarWidth = barWidth - gap;

    // Prepare gradient or solid color
    let fillStyle: string | CanvasGradient;
    if (Array.isArray(colors)) {
      // Create vertical gradient
      const gradient = ctx.createLinearGradient(0, height, 0, 0);
      const colorStops = colors.length;
      colors.forEach((color, index) => {
        gradient.addColorStop(index / (colorStops - 1), color);
      });
      fillStyle = gradient;
    } else {
      fillStyle = colors;
    }

    // Draw bars
    // Only use the lower frequency bins where most audio energy is
    const usableDataLength = Math.floor(frequencyData.length * (frequencyRange / 100));

    for (let i = 0; i < barCount; i++) {
      // Map bars to lower frequencies for better visualization
      const dataIndex = Math.floor((i / barCount) * usableDataLength);
      const value = frequencyData[dataIndex];

      // Normalize value (0-255 -> 0-1)
      const normalizedValue = value / 255;

      // Calculate bar height (with minimum height for aesthetics)
      const minHeight = height * 0.02;
      const barHeight = minHeight + (normalizedValue * (height - minHeight));

      // Calculate bar position
      const x = i * barWidth;
      const y = height - barHeight;

      // Draw reflection/shadow below bar
      if (normalizedValue > 0.2) {
        const reflectionGradient = ctx.createLinearGradient(0, height, 0, height - 100);
        reflectionGradient.addColorStop(0, Array.isArray(colors) ? colors[0] + '20' : colors + '20');
        reflectionGradient.addColorStop(1, 'transparent');
        ctx.fillStyle = reflectionGradient;
        ctx.fillRect(x, height, actualBarWidth, -80 * normalizedValue);
      }

      // Enhanced glow effect behind bar
      if (normalizedValue > 0.3) {
        ctx.shadowBlur = 40 * normalizedValue;
        ctx.shadowColor = Array.isArray(colors) ? colors[0] : colors;
        ctx.fillStyle = fillStyle;
        ctx.beginPath();
        ctx.roundRect(x, y, actualBarWidth, barHeight, [4, 4, 0, 0]);
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      // Main bar with gradient
      ctx.fillStyle = fillStyle;
      ctx.beginPath();
      ctx.roundRect(x, y, actualBarWidth, barHeight, [4, 4, 0, 0]);
      ctx.fill();

      // Add bright highlight on top for active bars
      if (normalizedValue > 0.6) {
        const highlightGradient = ctx.createLinearGradient(0, y, 0, y + 20);
        highlightGradient.addColorStop(0, 'rgba(255, 255, 255, 0.4)');
        highlightGradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
        ctx.fillStyle = highlightGradient;
        ctx.beginPath();
        ctx.roundRect(x, y, actualBarWidth, Math.min(20, barHeight), [4, 4, 0, 0]);
        ctx.fill();
      }

      // Add inner glow for intense peaks
      if (normalizedValue > 0.8) {
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(x + 1, y + 1, actualBarWidth - 2, barHeight - 2, [3, 3, 0, 0]);
        ctx.stroke();
      }
    }
  }, [frequencyData, colors, width, height, frequencyRange]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        width: `${width}px`,
        height: `${height}px`,
        display: 'block',
        position: 'absolute',
        top: 0,
        left: 0
      }}
    />
  );
};
