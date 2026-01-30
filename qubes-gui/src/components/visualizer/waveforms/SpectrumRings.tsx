import React, { useRef, useEffect } from 'react';

interface SpectrumRingsProps {
  frequencyData: Uint8Array;
  colors: string | string[];
  width: number;
  height: number;
  frequencyRange: number;
}

export const SpectrumRings: React.FC<SpectrumRingsProps> = ({
  frequencyData,
  colors,
  width,
  height,
  frequencyRange
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(0);
  const smoothedDataRef = useRef<number[]>([]);
  const rotationRef = useRef<number>(0);

  // Get colors array
  const getColors = (): string[] => {
    if (Array.isArray(colors)) {
      return colors;
    }
    return [colors, '#ffffff'];
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const colorArray = getColors();
    const centerX = width / 2;
    const centerY = height / 2;
    const maxRadius = Math.min(width, height) * 0.45;
    const innerRadius = maxRadius * 0.25;

    const animate = () => {
      // Get frequency data
      const dataLength = Math.floor(frequencyData.length * (frequencyRange / 100));
      const barCount = 64; // Number of bars around the circle

      // Initialize smoothed data if needed
      if (smoothedDataRef.current.length !== barCount) {
        smoothedDataRef.current = new Array(barCount).fill(0);
      }

      // Sample and smooth frequency data
      const smoothed = smoothedDataRef.current;
      for (let i = 0; i < barCount; i++) {
        const dataIndex = Math.floor((i / barCount) * dataLength);
        const value = frequencyData[dataIndex] / 255;
        // Smooth transition
        smoothed[i] = smoothed[i] * 0.7 + value * 0.3;
      }

      // Calculate overall intensity for effects
      let totalIntensity = 0;
      for (let i = 0; i < smoothed.length; i++) {
        totalIntensity += smoothed[i];
      }
      const avgIntensity = totalIntensity / smoothed.length;

      // Rotate slowly, faster with more intensity
      rotationRef.current += 0.002 + avgIntensity * 0.01;

      // Clear canvas
      ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
      ctx.fillRect(0, 0, width, height);

      // Draw background glow
      const bgGlow = ctx.createRadialGradient(
        centerX, centerY, innerRadius,
        centerX, centerY, maxRadius * 1.5
      );
      bgGlow.addColorStop(0, `${colorArray[0]}33`);
      bgGlow.addColorStop(0.5, `${colorArray[0]}11`);
      bgGlow.addColorStop(1, 'transparent');
      ctx.fillStyle = bgGlow;
      ctx.fillRect(0, 0, width, height);

      // Draw multiple ring layers
      const layers = 3;
      for (let layer = 0; layer < layers; layer++) {
        const layerRadius = innerRadius + (maxRadius - innerRadius) * (layer / layers);
        const layerMaxHeight = (maxRadius - innerRadius) / layers * 0.9;
        const layerAlpha = 1 - layer * 0.2;

        ctx.save();
        ctx.translate(centerX, centerY);
        ctx.rotate(rotationRef.current + layer * 0.5);

        const angleStep = (Math.PI * 2) / barCount;
        const barWidth = angleStep * 0.7;

        for (let i = 0; i < barCount; i++) {
          const angle = i * angleStep;
          const value = smoothed[(i + layer * 10) % barCount];
          const barHeight = layerMaxHeight * value;

          if (barHeight < 2) continue;

          // Calculate color based on position and value
          const colorIndex = (i / barCount) * (colorArray.length - 1);
          const colorStart = Math.floor(colorIndex);
          const colorEnd = Math.min(colorStart + 1, colorArray.length - 1);
          const colorMix = colorIndex - colorStart;

          // Get gradient colors
          const startColor = colorArray[colorStart];
          const endColor = colorArray[colorEnd];

          // Draw bar with gradient
          const innerX = Math.cos(angle) * layerRadius;
          const innerY = Math.sin(angle) * layerRadius;
          const outerX = Math.cos(angle) * (layerRadius + barHeight);
          const outerY = Math.sin(angle) * (layerRadius + barHeight);

          // Create gradient along the bar
          const gradient = ctx.createLinearGradient(innerX, innerY, outerX, outerY);
          gradient.addColorStop(0, `${startColor}${Math.floor(layerAlpha * 200).toString(16).padStart(2, '0')}`);
          gradient.addColorStop(1, `${endColor}${Math.floor(layerAlpha * 255 * value).toString(16).padStart(2, '0')}`);

          // Draw the bar as a wedge
          ctx.beginPath();
          ctx.arc(0, 0, layerRadius, angle - barWidth / 2, angle + barWidth / 2);
          ctx.arc(0, 0, layerRadius + barHeight, angle + barWidth / 2, angle - barWidth / 2, true);
          ctx.closePath();
          ctx.fillStyle = gradient;
          ctx.fill();

          // Add glow effect for high values
          if (value > 0.6) {
            ctx.shadowColor = startColor;
            ctx.shadowBlur = 15 * value;
            ctx.fill();
            ctx.shadowBlur = 0;
          }
        }

        ctx.restore();
      }

      // Draw center circle with pulsing glow
      const pulseSize = innerRadius * (0.8 + avgIntensity * 0.4);

      // Outer glow
      const centerGlow = ctx.createRadialGradient(
        centerX, centerY, 0,
        centerX, centerY, pulseSize * 1.5
      );
      centerGlow.addColorStop(0, `${colorArray[0]}aa`);
      centerGlow.addColorStop(0.5, `${colorArray[0]}44`);
      centerGlow.addColorStop(1, 'transparent');
      ctx.fillStyle = centerGlow;
      ctx.beginPath();
      ctx.arc(centerX, centerY, pulseSize * 1.5, 0, Math.PI * 2);
      ctx.fill();

      // Inner solid circle
      const innerGradient = ctx.createRadialGradient(
        centerX - pulseSize * 0.3, centerY - pulseSize * 0.3, 0,
        centerX, centerY, pulseSize
      );
      innerGradient.addColorStop(0, '#ffffff');
      innerGradient.addColorStop(0.3, colorArray[0]);
      innerGradient.addColorStop(1, `${colorArray[0]}88`);
      ctx.fillStyle = innerGradient;
      ctx.beginPath();
      ctx.arc(centerX, centerY, pulseSize, 0, Math.PI * 2);
      ctx.fill();

      // Add spinning highlight particles
      const particleCount = 8;
      for (let i = 0; i < particleCount; i++) {
        const particleAngle = rotationRef.current * 2 + (Math.PI * 2 * i) / particleCount;
        const particleRadius = maxRadius * 0.9;
        const px = centerX + Math.cos(particleAngle) * particleRadius;
        const py = centerY + Math.sin(particleAngle) * particleRadius;
        const particleSize = 3 + avgIntensity * 5;

        const particleGlow = ctx.createRadialGradient(px, py, 0, px, py, particleSize * 3);
        particleGlow.addColorStop(0, '#ffffff');
        particleGlow.addColorStop(0.3, `${colorArray[i % colorArray.length]}cc`);
        particleGlow.addColorStop(1, 'transparent');

        ctx.fillStyle = particleGlow;
        ctx.beginPath();
        ctx.arc(px, py, particleSize * 3, 0, Math.PI * 2);
        ctx.fill();
      }

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationRef.current);
    };
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
