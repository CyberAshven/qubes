import React, { useEffect, useRef } from 'react';

interface ConcentricCirclesProps {
  frequencyData: Uint8Array;
  colors: string | string[];
  width: number;
  height: number;
  frequencyRange: number;
}

export const ConcentricCircles: React.FC<ConcentricCirclesProps> = ({
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
    const maxRadius = Math.min(width, height) * 0.45;
    const ringCount = 32;
    const ringSpacing = maxRadius / ringCount;

    const usableDataLength = Math.floor(frequencyData.length * (frequencyRange / 100));
    const primaryColor = Array.isArray(colors) ? colors[0] : colors;

    // Draw from outside to inside for proper layering
    for (let i = ringCount - 1; i >= 0; i--) {
      const dataIndex = Math.floor((i / ringCount) * usableDataLength);
      const value = frequencyData[dataIndex];
      const normalizedValue = value / 255;

      const radius = (i + 1) * ringSpacing + (normalizedValue * ringSpacing * 0.5);
      const lineWidth = Math.max(2, ringSpacing * 0.6 + normalizedValue * ringSpacing * 0.4);

      // Create color gradient for each ring
      let strokeStyle: string | CanvasGradient;
      if (Array.isArray(colors)) {
        const colorIndex = Math.floor((i / ringCount) * (colors.length - 1));
        strokeStyle = colors[colorIndex];
      } else {
        const alpha = Math.floor((0.3 + normalizedValue * 0.7) * 255).toString(16).padStart(2, '0');
        strokeStyle = colors + alpha;
      }

      // Draw outer glow
      if (normalizedValue > 0.3) {
        ctx.shadowBlur = 30 * normalizedValue;
        ctx.shadowColor = primaryColor;
      }

      // Draw main ring
      ctx.strokeStyle = strokeStyle;
      ctx.lineWidth = lineWidth;
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
      ctx.stroke();

      ctx.shadowBlur = 0;

      // Draw bright highlight arc for active rings
      if (normalizedValue > 0.5) {
        const highlightGradient = ctx.createRadialGradient(
          centerX - radius * 0.3, centerY - radius * 0.3, 0,
          centerX, centerY, radius
        );
        highlightGradient.addColorStop(0, 'rgba(255, 255, 255, 0.6)');
        highlightGradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

        ctx.strokeStyle = highlightGradient;
        ctx.lineWidth = lineWidth * 0.5;
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, -Math.PI, -Math.PI / 4);
        ctx.stroke();
      }

      // Add pulsing particles on high-energy rings
      if (normalizedValue > 0.7) {
        const particleCount = 8;
        for (let p = 0; p < particleCount; p++) {
          const angle = (p / particleCount) * Math.PI * 2 + Date.now() / 1000;
          const px = centerX + Math.cos(angle) * radius;
          const py = centerY + Math.sin(angle) * radius;

          ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
          ctx.shadowBlur = 20;
          ctx.shadowColor = primaryColor;
          ctx.beginPath();
          ctx.arc(px, py, 3 + normalizedValue * 3, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.shadowBlur = 0;
      }
    }

    // Draw center orb with pulsing effect
    const avgIntensity = frequencyData.slice(0, usableDataLength).reduce((a, b) => a + b, 0) / usableDataLength / 255;
    const centerRadius = 20 + avgIntensity * 40;

    const centerGradient = ctx.createRadialGradient(
      centerX - centerRadius * 0.4, centerY - centerRadius * 0.4, 0,
      centerX, centerY, centerRadius
    );
    centerGradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
    centerGradient.addColorStop(0.3, primaryColor);
    centerGradient.addColorStop(1, primaryColor + '80');

    ctx.fillStyle = centerGradient;
    ctx.shadowBlur = 50;
    ctx.shadowColor = primaryColor;
    ctx.beginPath();
    ctx.arc(centerX, centerY, centerRadius, 0, Math.PI * 2);
    ctx.fill();

    ctx.shadowBlur = 0;

    // Draw center highlight
    ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
    ctx.beginPath();
    ctx.arc(centerX - centerRadius * 0.3, centerY - centerRadius * 0.3, centerRadius * 0.4, 0, Math.PI * 2);
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
