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
  const animationRef = useRef<number>(0);
  const glowIntensityRef = useRef<number>(0);

  const getColor = () => {
    if (Array.isArray(colors) && colors.length > 0) return colors[0];
    return typeof colors === 'string' ? colors : '#ff00ff';
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
    const barCount = 48;

    const animate = () => {
      const centerY = height / 2;

      // Background
      ctx.fillStyle = '#050510';
      ctx.fillRect(0, 0, width, height);

      // Horizontal grid lines
      ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.05)`;
      ctx.lineWidth = 1;
      for (let y = 0; y < height; y += 20) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Center line glow
      const usableDataLength = Math.floor(frequencyData.length * (frequencyRange / 100));
      let totalIntensity = 0;

      for (let i = 0; i < usableDataLength; i++) {
        totalIntensity += frequencyData[i];
      }
      const avgIntensity = totalIntensity / usableDataLength / 255;
      glowIntensityRef.current = glowIntensityRef.current * 0.9 + avgIntensity * 0.1;

      // Pulsing center line
      const centerGlow = ctx.createLinearGradient(0, centerY - 50, 0, centerY + 50);
      centerGlow.addColorStop(0, 'transparent');
      centerGlow.addColorStop(0.5, `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${0.2 + glowIntensityRef.current * 0.5})`);
      centerGlow.addColorStop(1, 'transparent');
      ctx.fillStyle = centerGlow;
      ctx.fillRect(0, centerY - 50, width, 100);

      const barWidth = width / barCount;
      const gap = Math.max(3, barWidth * 0.25);
      const actualBarWidth = barWidth - gap;
      const maxBarHeight = height / 2 - 30;

      for (let i = 0; i < barCount; i++) {
        const dataIndex = Math.floor((i / barCount) * usableDataLength);
        const value = dataIndex < 2 ? 0 : frequencyData[dataIndex];
        const normalizedValue = value / 255;

        if (normalizedValue < 0.03) continue;

        const barHeight = normalizedValue * maxBarHeight;
        const x = i * barWidth + gap / 2;

        // Color shift for intensity
        let r = rgb.r, g = rgb.g, b = rgb.b;
        if (normalizedValue > 0.6) {
          r = Math.min(255, r + 80);
          g = Math.max(0, g - 30);
        }

        // Glow layers
        for (let glow = 2; glow >= 0; glow--) {
          const alpha = (0.2 - glow * 0.06) * normalizedValue;
          ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
          // Top bar
          ctx.fillRect(x - glow * 2, centerY - barHeight - glow * 2, actualBarWidth + glow * 4, barHeight + glow * 2);
          // Bottom bar (mirrored)
          ctx.fillRect(x - glow * 2, centerY - glow * 2, actualBarWidth + glow * 4, barHeight + glow * 2);
        }

        // Top bar gradient
        const topGrad = ctx.createLinearGradient(x, centerY, x, centerY - barHeight);
        topGrad.addColorStop(0, `rgba(255, 255, 255, 0.9)`);
        topGrad.addColorStop(0.3, `rgba(${r}, ${g}, ${b}, 1)`);
        topGrad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0.7)`);
        ctx.fillStyle = topGrad;
        ctx.fillRect(x, centerY - barHeight, actualBarWidth, barHeight);

        // Bottom bar gradient (mirrored)
        const bottomGrad = ctx.createLinearGradient(x, centerY, x, centerY + barHeight);
        bottomGrad.addColorStop(0, `rgba(255, 255, 255, 0.9)`);
        bottomGrad.addColorStop(0.3, `rgba(${r}, ${g}, ${b}, 1)`);
        bottomGrad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0.7)`);
        ctx.fillStyle = bottomGrad;
        ctx.fillRect(x, centerY, actualBarWidth, barHeight);

        // Bright tips for high values
        if (normalizedValue > 0.5) {
          ctx.fillStyle = `rgba(255, 255, 255, ${normalizedValue})`;
          ctx.shadowColor = '#ffffff';
          ctx.shadowBlur = 15;
          ctx.fillRect(x, centerY - barHeight - 2, actualBarWidth, 4);
          ctx.fillRect(x, centerY + barHeight - 2, actualBarWidth, 4);
          ctx.shadowBlur = 0;
        }
      }

      // Center line
      ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.8)`;
      ctx.lineWidth = 2;
      ctx.shadowColor = primaryColor;
      ctx.shadowBlur = 10;
      ctx.beginPath();
      ctx.moveTo(0, centerY);
      ctx.lineTo(width, centerY);
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Corner elements
      ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.4)`;
      ctx.lineWidth = 2;
      const cs = 20;
      [[15, 15], [width - 15, 15], [15, height - 15], [width - 15, height - 15]].forEach(([cx, cy]) => {
        const dx = cx < width / 2 ? 1 : -1;
        const dy = cy < height / 2 ? 1 : -1;
        ctx.beginPath();
        ctx.moveTo(cx, cy + cs * dy);
        ctx.lineTo(cx, cy);
        ctx.lineTo(cx + cs * dx, cy);
        ctx.stroke();
      });

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
