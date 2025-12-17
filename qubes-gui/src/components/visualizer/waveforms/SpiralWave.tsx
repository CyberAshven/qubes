import React, { useEffect, useRef } from 'react';

interface SpiralWaveProps {
  frequencyData: Uint8Array;
  colors: string | string[];
  width: number;
  height: number;
  frequencyRange: number;
}

export const SpiralWave: React.FC<SpiralWaveProps> = ({
  frequencyData,
  colors,
  width,
  height,
  frequencyRange
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rotationRef = useRef(0);

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
    const spiralCount = 3; // Multiple spiral arms
    const pointsPerSpiral = 256;

    rotationRef.current += 0.01;

    const usableDataLength = Math.floor(frequencyData.length * (frequencyRange / 100));
    const primaryColor = Array.isArray(colors) ? colors[0] : colors;

    // Draw each spiral arm
    for (let spiral = 0; spiral < spiralCount; spiral++) {
      const spiralOffset = (spiral / spiralCount) * Math.PI * 2;

      const points: { x: number; y: number; value: number }[] = [];

      // Generate spiral points
      for (let i = 0; i < pointsPerSpiral; i++) {
        const progress = i / pointsPerSpiral;
        const dataIndex = Math.floor(progress * usableDataLength);
        const value = frequencyData[dataIndex];
        const normalizedValue = value / 255;

        // Spiral equation
        const angle = progress * Math.PI * 6 + spiralOffset + rotationRef.current;
        const radius = progress * maxRadius;

        // Add audio-reactive displacement
        const displacement = normalizedValue * 50;
        const actualRadius = radius + displacement;

        const x = centerX + Math.cos(angle) * actualRadius;
        const y = centerY + Math.sin(angle) * actualRadius;

        points.push({ x, y, value: normalizedValue });
      }

      // Draw glow trail
      for (let glowLayer = 4; glowLayer > 0; glowLayer--) {
        ctx.strokeStyle = primaryColor + Math.floor(20 / glowLayer).toString(16).padStart(2, '0');
        ctx.lineWidth = glowLayer * 6;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.shadowBlur = glowLayer * 10;
        ctx.shadowColor = primaryColor;

        ctx.beginPath();
        ctx.moveTo(points[0].x, points[0].y);

        for (let i = 1; i < points.length - 2; i++) {
          const xc = (points[i].x + points[i + 1].x) / 2;
          const yc = (points[i].y + points[i + 1].y) / 2;
          ctx.quadraticCurveTo(points[i].x, points[i].y, xc, yc);
        }

        ctx.stroke();
      }

      ctx.shadowBlur = 0;

      // Draw main spiral with gradient
      let strokeStyle: string | CanvasGradient;
      if (Array.isArray(colors) && colors.length > 1) {
        const gradient = ctx.createLinearGradient(centerX, centerY, centerX + maxRadius, centerY + maxRadius);
        colors.forEach((color, index) => {
          gradient.addColorStop(index / (colors.length - 1), color);
        });
        strokeStyle = gradient;
      } else {
        strokeStyle = primaryColor;
      }

      ctx.strokeStyle = strokeStyle;
      ctx.lineWidth = 3;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);

      for (let i = 1; i < points.length - 2; i++) {
        const xc = (points[i].x + points[i + 1].x) / 2;
        const yc = (points[i].y + points[i + 1].y) / 2;
        ctx.quadraticCurveTo(points[i].x, points[i].y, xc, yc);
      }

      ctx.stroke();

      // Draw bright highlight line
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
      ctx.lineWidth = 1.5;
      ctx.shadowBlur = 8;
      ctx.shadowColor = 'rgba(255, 255, 255, 0.8)';

      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);

      for (let i = 1; i < points.length - 2; i++) {
        const xc = (points[i].x + points[i + 1].x) / 2;
        const yc = (points[i].y + points[i + 1].y) / 2;
        ctx.quadraticCurveTo(points[i].x, points[i].y, xc, yc);
      }

      ctx.stroke();
      ctx.shadowBlur = 0;

      // Draw particles along spiral for high-energy sections
      for (let i = 0; i < points.length; i += 12) {
        const point = points[i];
        if (point.value > 0.6) {
          ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
          ctx.shadowBlur = 20;
          ctx.shadowColor = primaryColor;
          ctx.beginPath();
          ctx.arc(point.x, point.y, 4 * point.value, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      ctx.shadowBlur = 0;
    }

    // Draw center orb
    const centerGradient = ctx.createRadialGradient(
      centerX - 15, centerY - 15, 0,
      centerX, centerY, 30
    );
    centerGradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
    centerGradient.addColorStop(0.4, primaryColor);
    centerGradient.addColorStop(1, primaryColor + '60');

    ctx.fillStyle = centerGradient;
    ctx.shadowBlur = 50;
    ctx.shadowColor = primaryColor;
    ctx.beginPath();
    ctx.arc(centerX, centerY, 30, 0, Math.PI * 2);
    ctx.fill();

    ctx.shadowBlur = 0;
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
