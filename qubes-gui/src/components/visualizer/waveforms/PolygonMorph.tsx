import React, { useEffect, useRef } from 'react';

interface PolygonMorphProps {
  frequencyData: Uint8Array;
  colors: string | string[];
  width: number;
  height: number;
  frequencyRange: number;
}

export const PolygonMorph: React.FC<PolygonMorphProps> = ({
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
    const sides = 64; // More sides for smoother morphing
    const baseRadius = Math.min(width, height) * 0.25;
    const usableDataLength = Math.floor(frequencyData.length * (frequencyRange / 100));

    // Increment rotation
    rotationRef.current += 0.005;

    const primaryColor = Array.isArray(colors) ? colors[0] : colors;

    // Draw outer glow rings
    for (let ring = 5; ring > 0; ring--) {
      const ringGradient = ctx.createRadialGradient(
        centerX, centerY, baseRadius * 0.8,
        centerX, centerY, baseRadius * 1.5 + ring * 30
      );
      ringGradient.addColorStop(0, 'transparent');
      ringGradient.addColorStop(1, primaryColor + Math.floor(20 / ring).toString(16).padStart(2, '0'));

      ctx.fillStyle = ringGradient;
      ctx.beginPath();
      ctx.arc(centerX, centerY, baseRadius * 1.5 + ring * 30, 0, Math.PI * 2);
      ctx.fill();
    }

    // Calculate polygon points with audio-reactive morphing
    const points: { x: number; y: number; value: number }[] = [];
    for (let i = 0; i < sides; i++) {
      const angle = (i / sides) * Math.PI * 2 + rotationRef.current;
      const dataIndex = Math.floor((i / sides) * usableDataLength);
      const value = frequencyData[dataIndex];
      const normalizedValue = value / 255;

      // Morph radius based on audio
      const morphedRadius = baseRadius + (normalizedValue * baseRadius * 0.6);

      const x = centerX + Math.cos(angle) * morphedRadius;
      const y = centerY + Math.sin(angle) * morphedRadius;

      points.push({ x, y, value: normalizedValue });
    }

    // Draw filled polygon with gradient
    let fillStyle: string | CanvasGradient;
    if (Array.isArray(colors)) {
      const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, baseRadius * 1.5);
      colors.forEach((color, index) => {
        gradient.addColorStop(index / (colors.length - 1), color + '60');
      });
      fillStyle = gradient;
    } else {
      const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, baseRadius * 1.5);
      gradient.addColorStop(0, colors + '80');
      gradient.addColorStop(1, colors + '20');
      fillStyle = gradient;
    }

    ctx.fillStyle = fillStyle;
    ctx.shadowBlur = 40;
    ctx.shadowColor = primaryColor;
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < points.length; i++) {
      const xc = (points[i].x + points[(i + 1) % points.length].x) / 2;
      const yc = (points[i].y + points[(i + 1) % points.length].y) / 2;
      ctx.quadraticCurveTo(points[i].x, points[i].y, xc, yc);
    }
    ctx.closePath();
    ctx.fill();

    // Draw outline
    ctx.strokeStyle = primaryColor;
    ctx.lineWidth = 3;
    ctx.shadowBlur = 20;
    ctx.shadowColor = primaryColor;
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < points.length; i++) {
      const xc = (points[i].x + points[(i + 1) % points.length].x) / 2;
      const yc = (points[i].y + points[(i + 1) % points.length].y) / 2;
      ctx.quadraticCurveTo(points[i].x, points[i].y, xc, yc);
    }
    ctx.closePath();
    ctx.stroke();

    ctx.shadowBlur = 0;

    // Draw bright highlight outline
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < points.length; i++) {
      const xc = (points[i].x + points[(i + 1) % points.length].x) / 2;
      const yc = (points[i].y + points[(i + 1) % points.length].y) / 2;
      ctx.quadraticCurveTo(points[i].x, points[i].y, xc, yc);
    }
    ctx.closePath();
    ctx.stroke();

    // Draw vertices with glow for high-energy points
    for (let i = 0; i < points.length; i += 4) {
      const point = points[i];
      if (point.value > 0.6) {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
        ctx.shadowBlur = 25;
        ctx.shadowColor = primaryColor;
        ctx.beginPath();
        ctx.arc(point.x, point.y, 5 * point.value, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    ctx.shadowBlur = 0;

    // Draw center orb
    const orbGradient = ctx.createRadialGradient(
      centerX - 20, centerY - 20, 0,
      centerX, centerY, baseRadius * 0.3
    );
    orbGradient.addColorStop(0, 'rgba(255, 255, 255, 0.9)');
    orbGradient.addColorStop(0.3, primaryColor);
    orbGradient.addColorStop(1, primaryColor + '60');

    ctx.fillStyle = orbGradient;
    ctx.shadowBlur = 40;
    ctx.shadowColor = primaryColor;
    ctx.beginPath();
    ctx.arc(centerX, centerY, baseRadius * 0.3, 0, Math.PI * 2);
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
