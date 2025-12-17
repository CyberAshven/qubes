import React, { useEffect, useRef } from 'react';

interface RadialSpectrumProps {
  frequencyData: Uint8Array;
  colors: string | string[];
  width: number;
  height: number;
  frequencyRange: number;
}

export const RadialSpectrum: React.FC<RadialSpectrumProps> = ({
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

    const centerX = width / 2;
    const centerY = height / 2;
    const barCount = 128;
    const angleStep = (Math.PI * 2) / barCount;
    const innerRadius = Math.min(width, height) * 0.1;
    const maxBarLength = Math.min(width, height) * 0.4;

    const usableDataLength = Math.floor(frequencyData.length * (frequencyRange / 100));

    // Draw center glow
    const centerGradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, innerRadius + 50);
    const primaryColor = Array.isArray(colors) ? colors[0] : colors;
    centerGradient.addColorStop(0, primaryColor + 'AA');
    centerGradient.addColorStop(0.5, primaryColor + '40');
    centerGradient.addColorStop(1, 'transparent');
    ctx.fillStyle = centerGradient;
    ctx.beginPath();
    ctx.arc(centerX, centerY, innerRadius + 50, 0, Math.PI * 2);
    ctx.fill();

    for (let i = 0; i < barCount; i++) {
      const angle = i * angleStep - Math.PI / 2; // Start from top
      const dataIndex = Math.floor((i / barCount) * usableDataLength);
      const value = frequencyData[dataIndex];
      const normalizedValue = value / 255;

      const barLength = normalizedValue * maxBarLength;

      // Calculate bar endpoints
      const startX = centerX + Math.cos(angle) * innerRadius;
      const startY = centerY + Math.sin(angle) * innerRadius;
      const endX = centerX + Math.cos(angle) * (innerRadius + barLength);
      const endY = centerY + Math.sin(angle) * (innerRadius + barLength);

      // Draw glow behind bar
      if (normalizedValue > 0.3) {
        ctx.shadowBlur = 30 * normalizedValue;
        ctx.shadowColor = primaryColor;
      }

      // Create gradient for each bar
      const barGradient = ctx.createLinearGradient(startX, startY, endX, endY);
      if (Array.isArray(colors)) {
        colors.forEach((color, index) => {
          barGradient.addColorStop(index / (colors.length - 1), color);
        });
      } else {
        barGradient.addColorStop(0, colors + 'AA');
        barGradient.addColorStop(1, colors);
      }

      // Draw bar
      ctx.strokeStyle = barGradient;
      ctx.lineWidth = Math.max(2, (Math.PI * 2 * innerRadius) / barCount - 2);
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(startX, startY);
      ctx.lineTo(endX, endY);
      ctx.stroke();

      ctx.shadowBlur = 0;

      // Draw bright tip for active bars
      if (normalizedValue > 0.6) {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
        ctx.shadowBlur = 20;
        ctx.shadowColor = 'rgba(255, 255, 255, 0.8)';
        ctx.beginPath();
        ctx.arc(endX, endY, 4 * normalizedValue, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
      }
    }

    // Draw center circle
    ctx.fillStyle = primaryColor;
    ctx.shadowBlur = 30;
    ctx.shadowColor = primaryColor;
    ctx.beginPath();
    ctx.arc(centerX, centerY, innerRadius, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;

    // Draw center highlight
    const highlightGradient = ctx.createRadialGradient(
      centerX - innerRadius / 3,
      centerY - innerRadius / 3,
      0,
      centerX,
      centerY,
      innerRadius
    );
    highlightGradient.addColorStop(0, 'rgba(255, 255, 255, 0.6)');
    highlightGradient.addColorStop(0.5, 'rgba(255, 255, 255, 0.2)');
    highlightGradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
    ctx.fillStyle = highlightGradient;
    ctx.beginPath();
    ctx.arc(centerX, centerY, innerRadius, 0, Math.PI * 2);
    ctx.fill();
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
