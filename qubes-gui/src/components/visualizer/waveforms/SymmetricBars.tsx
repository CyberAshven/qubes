import React, { useEffect, useRef } from 'react';

interface SymmetricBarsProps {
  frequencyData: Uint8Array;
  colors: string | string[];
  width: number;
  height: number;
  frequencyRange: number;
}

export const SymmetricBars: React.FC<SymmetricBarsProps> = ({
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

    canvas.width = width;
    canvas.height = height;
    ctx.clearRect(0, 0, width, height);

    const centerY = height / 2;
    const barCount = 64;
    const barWidth = width / barCount;
    const gap = Math.max(3, barWidth * 0.15);
    const actualBarWidth = barWidth - gap;

    // Prepare gradient or solid color
    let fillStyle: string | CanvasGradient;
    if (Array.isArray(colors)) {
      const gradient = ctx.createLinearGradient(0, centerY - height / 2, 0, centerY + height / 2);
      const colorStops = colors.length;
      colors.forEach((color, index) => {
        gradient.addColorStop(index / (colorStops - 1), color);
      });
      fillStyle = gradient;
    } else {
      fillStyle = colors;
    }

    const usableDataLength = Math.floor(frequencyData.length * (frequencyRange / 100));

    for (let i = 0; i < barCount; i++) {
      const dataIndex = Math.floor((i / barCount) * usableDataLength);
      const value = frequencyData[dataIndex];
      const normalizedValue = value / 255;

      const maxBarHeight = height / 2 - 20;
      const barHeight = normalizedValue * maxBarHeight;

      const x = i * barWidth;

      // Draw reflection/glow in center
      if (normalizedValue > 0.2) {
        const glowGradient = ctx.createRadialGradient(
          x + actualBarWidth / 2, centerY, 0,
          x + actualBarWidth / 2, centerY, barHeight + 50
        );
        glowGradient.addColorStop(0, Array.isArray(colors) ? colors[0] + '40' : colors + '40');
        glowGradient.addColorStop(1, 'transparent');
        ctx.fillStyle = glowGradient;
        ctx.fillRect(x, centerY - barHeight - 25, actualBarWidth, barHeight * 2 + 50);
      }

      // Enhanced glow effect
      if (normalizedValue > 0.3) {
        ctx.shadowBlur = 50 * normalizedValue;
        ctx.shadowColor = Array.isArray(colors) ? colors[0] : colors;
      }

      // Top bar (mirrored upward)
      ctx.fillStyle = fillStyle;
      ctx.beginPath();
      ctx.roundRect(x, centerY - barHeight, actualBarWidth, barHeight, [4, 4, 0, 0]);
      ctx.fill();

      // Bottom bar (mirrored downward)
      ctx.beginPath();
      ctx.roundRect(x, centerY, actualBarWidth, barHeight, [0, 0, 4, 4]);
      ctx.fill();

      ctx.shadowBlur = 0;

      // Add bright highlights
      if (normalizedValue > 0.6) {
        const highlightGradient = ctx.createLinearGradient(0, centerY - barHeight, 0, centerY - barHeight + 15);
        highlightGradient.addColorStop(0, 'rgba(255, 255, 255, 0.5)');
        highlightGradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
        ctx.fillStyle = highlightGradient;
        ctx.fillRect(x, centerY - barHeight, actualBarWidth, Math.min(15, barHeight));

        // Bottom highlight
        const highlightGradient2 = ctx.createLinearGradient(0, centerY + barHeight, 0, centerY + barHeight - 15);
        highlightGradient2.addColorStop(0, 'rgba(255, 255, 255, 0.5)');
        highlightGradient2.addColorStop(1, 'rgba(255, 255, 255, 0)');
        ctx.fillStyle = highlightGradient2;
        ctx.fillRect(x, centerY + barHeight - 15, actualBarWidth, 15);
      }

      // Center line glow
      if (normalizedValue > 0.5) {
        ctx.strokeStyle = Array.isArray(colors) ? colors[0] + '80' : colors + '80';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(x, centerY);
        ctx.lineTo(x + actualBarWidth, centerY);
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
