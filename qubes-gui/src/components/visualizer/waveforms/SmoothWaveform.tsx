import React, { useEffect, useRef } from 'react';

interface SmoothWaveformProps {
  frequencyData: Uint8Array;
  colors: string | string[];
  width: number;
  height: number;
  frequencyRange: number;
}

export const SmoothWaveform: React.FC<SmoothWaveformProps> = ({
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
    const sampleCount = 256;
    const usableDataLength = Math.floor(frequencyData.length * (frequencyRange / 100));

    // Create smooth waveform points
    const points: { x: number; y: number }[] = [];
    for (let i = 0; i < sampleCount; i++) {
      const dataIndex = Math.floor((i / sampleCount) * usableDataLength);
      const value = frequencyData[dataIndex];
      const normalizedValue = value / 255;

      const x = (i / sampleCount) * width;
      const amplitude = normalizedValue * (height / 2 - 40);
      const y = centerY + Math.sin((i / sampleCount) * Math.PI * 2) * amplitude;

      points.push({ x, y });
    }

    // Get primary color
    const primaryColor = Array.isArray(colors) ? colors[0] : colors;

    // Draw glow layers (multiple layers for intensity)
    for (let glowLayer = 5; glowLayer > 0; glowLayer--) {
      ctx.strokeStyle = primaryColor + Math.floor(30 / glowLayer).toString(16).padStart(2, '0');
      ctx.lineWidth = glowLayer * 8;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.shadowBlur = glowLayer * 15;
      ctx.shadowColor = primaryColor;

      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);

      // Draw smooth curve using quadratic curves
      for (let i = 1; i < points.length - 2; i++) {
        const xc = (points[i].x + points[i + 1].x) / 2;
        const yc = (points[i].y + points[i + 1].y) / 2;
        ctx.quadraticCurveTo(points[i].x, points[i].y, xc, yc);
      }

      ctx.stroke();
    }

    ctx.shadowBlur = 0;

    // Draw main waveform with gradient
    let strokeStyle: string | CanvasGradient;
    if (Array.isArray(colors) && colors.length > 1) {
      const gradient = ctx.createLinearGradient(0, 0, width, 0);
      colors.forEach((color, index) => {
        gradient.addColorStop(index / (colors.length - 1), color);
      });
      strokeStyle = gradient;
    } else {
      strokeStyle = primaryColor;
    }

    ctx.strokeStyle = strokeStyle;
    ctx.lineWidth = 4;
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

    // Draw bright highlight line on top
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
    ctx.lineWidth = 2;
    ctx.shadowBlur = 10;
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

    // Draw particles along the wave for extra flair
    for (let i = 0; i < points.length; i += 8) {
      const point = points[i];
      const dataIndex = Math.floor((i / sampleCount) * usableDataLength);
      const value = frequencyData[dataIndex];
      const normalizedValue = value / 255;

      if (normalizedValue > 0.5) {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
        ctx.shadowBlur = 20;
        ctx.shadowColor = primaryColor;
        ctx.beginPath();
        ctx.arc(point.x, point.y, 3 * normalizedValue, 0, Math.PI * 2);
        ctx.fill();
      }
    }

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
