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
  const animationRef = useRef<number>(0);
  const rotationRef = useRef<number>(0);
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
    const barCount = 72;

    // Initialize peaks
    if (peaksRef.current.length !== barCount) {
      peaksRef.current = new Array(barCount).fill(0);
    }

    const animate = () => {
      rotationRef.current += 0.003;

      const centerX = width / 2;
      const centerY = height / 2;
      const innerRadius = Math.min(width, height) * 0.12;
      const maxBarLength = Math.min(width, height) * 0.35;

      // Dark background with radial gradient
      const bgGrad = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, Math.max(width, height) * 0.7);
      bgGrad.addColorStop(0, '#0a0a15');
      bgGrad.addColorStop(1, '#020205');
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, width, height);

      // Circular grid lines
      ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.06)`;
      ctx.lineWidth = 1;
      for (let r = innerRadius; r < maxBarLength + innerRadius; r += 40) {
        ctx.beginPath();
        ctx.arc(centerX, centerY, r, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Radial grid lines
      for (let i = 0; i < 12; i++) {
        const angle = (i / 12) * Math.PI * 2;
        ctx.beginPath();
        ctx.moveTo(centerX + Math.cos(angle) * innerRadius, centerY + Math.sin(angle) * innerRadius);
        ctx.lineTo(centerX + Math.cos(angle) * (innerRadius + maxBarLength + 20), centerY + Math.sin(angle) * (innerRadius + maxBarLength + 20));
        ctx.stroke();
      }

      const usableDataLength = Math.floor(frequencyData.length * (frequencyRange / 100));
      const angleStep = (Math.PI * 2) / barCount;
      const peaks = peaksRef.current;

      // Draw bars
      for (let i = 0; i < barCount; i++) {
        const angle = i * angleStep - Math.PI / 2 + rotationRef.current;
        const dataIndex = Math.floor((i / barCount) * usableDataLength);
        // Skip first 2 bins (DC offset)
        const value = dataIndex < 2 ? 0 : frequencyData[dataIndex];
        const normalizedValue = value / 255;

        // Update peak
        if (normalizedValue > peaks[i]) {
          peaks[i] = normalizedValue;
        } else {
          peaks[i] = Math.max(0, peaks[i] - 0.015);
        }

        // Skip low values
        if (normalizedValue < 0.03) continue;

        const barLength = normalizedValue * maxBarLength;

        const startX = centerX + Math.cos(angle) * innerRadius;
        const startY = centerY + Math.sin(angle) * innerRadius;
        const endX = centerX + Math.cos(angle) * (innerRadius + barLength);
        const endY = centerY + Math.sin(angle) * (innerRadius + barLength);

        // Color shift for intensity
        let r = rgb.r, g = rgb.g, b = rgb.b;
        if (normalizedValue > 0.7) {
          r = Math.min(255, rgb.r + 80);
          g = Math.max(0, rgb.g - 40);
        }

        // Glow layers
        for (let glow = 2; glow >= 0; glow--) {
          ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${(0.15 - glow * 0.05) * normalizedValue})`;
          ctx.lineWidth = 6 + glow * 4;
          ctx.lineCap = 'round';
          ctx.beginPath();
          ctx.moveTo(startX, startY);
          ctx.lineTo(endX, endY);
          ctx.stroke();
        }

        // Main bar with gradient
        const barGrad = ctx.createLinearGradient(startX, startY, endX, endY);
        barGrad.addColorStop(0, `rgba(255, 255, 255, 0.9)`);
        barGrad.addColorStop(0.3, `rgba(${r}, ${g}, ${b}, 1)`);
        barGrad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0.8)`);
        ctx.strokeStyle = barGrad;
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(startX, startY);
        ctx.lineTo(endX, endY);
        ctx.stroke();

        // Peak indicator
        if (peaks[i] > 0.05) {
          const peakDist = innerRadius + peaks[i] * maxBarLength + 8;
          const peakX = centerX + Math.cos(angle) * peakDist;
          const peakY = centerY + Math.sin(angle) * peakDist;
          ctx.fillStyle = '#ffffff';
          ctx.shadowColor = primaryColor;
          ctx.shadowBlur = 10;
          ctx.beginPath();
          ctx.arc(peakX, peakY, 2, 0, Math.PI * 2);
          ctx.fill();
          ctx.shadowBlur = 0;
        }

        // Bright tip for high values
        if (normalizedValue > 0.6) {
          ctx.fillStyle = `rgba(255, 255, 255, ${normalizedValue})`;
          ctx.shadowColor = '#ffffff';
          ctx.shadowBlur = 15;
          ctx.beginPath();
          ctx.arc(endX, endY, 4 * normalizedValue, 0, Math.PI * 2);
          ctx.fill();
          ctx.shadowBlur = 0;
        }
      }

      // Center orb with pulse
      let totalIntensity = 0;
      for (let i = 2; i < usableDataLength; i++) {
        totalIntensity += frequencyData[i];
      }
      const avgIntensity = totalIntensity / (usableDataLength - 2) / 255;

      // Outer glow
      const orbGlow = ctx.createRadialGradient(centerX, centerY, innerRadius * 0.5, centerX, centerY, innerRadius * 1.5);
      orbGlow.addColorStop(0, `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${0.3 + avgIntensity * 0.4})`);
      orbGlow.addColorStop(1, 'transparent');
      ctx.fillStyle = orbGlow;
      ctx.beginPath();
      ctx.arc(centerX, centerY, innerRadius * 1.5, 0, Math.PI * 2);
      ctx.fill();

      // Main orb
      const orbGrad = ctx.createRadialGradient(centerX - innerRadius * 0.3, centerY - innerRadius * 0.3, 0, centerX, centerY, innerRadius);
      orbGrad.addColorStop(0, '#ffffff');
      orbGrad.addColorStop(0.3, primaryColor);
      orbGrad.addColorStop(1, `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.8)`);
      ctx.fillStyle = orbGrad;
      ctx.shadowColor = primaryColor;
      ctx.shadowBlur = 30 + avgIntensity * 20;
      ctx.beginPath();
      ctx.arc(centerX, centerY, innerRadius, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;

      // Orb ring
      ctx.strokeStyle = `rgba(255, 255, 255, 0.6)`;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(centerX, centerY, innerRadius, 0, Math.PI * 2);
      ctx.stroke();

      // Corner brackets
      ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.4)`;
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
