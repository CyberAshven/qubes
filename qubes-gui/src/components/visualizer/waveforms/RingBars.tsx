import React, { useEffect, useRef } from 'react';

interface RingBarsProps {
  frequencyData: Uint8Array;
  colors: string | string[];
  width: number;
  height: number;
  frequencyRange: number;
}

export const RingBars: React.FC<RingBarsProps> = ({
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
    const barCount = 96;
    const ringRadius = Math.min(width, height) * 0.25;
    const maxBarHeight = Math.min(width, height) * 0.2;

    rotationRef.current += 0.003;

    const usableDataLength = Math.floor(frequencyData.length * (frequencyRange / 100));
    const primaryColor = Array.isArray(colors) ? colors[0] : colors;

    // Draw ambient glow
    const ambientGradient = ctx.createRadialGradient(
      centerX, centerY, ringRadius * 0.5,
      centerX, centerY, ringRadius + maxBarHeight + 100
    );
    ambientGradient.addColorStop(0, 'transparent');
    ambientGradient.addColorStop(0.7, primaryColor + '20');
    ambientGradient.addColorStop(1, 'transparent');
    ctx.fillStyle = ambientGradient;
    ctx.beginPath();
    ctx.arc(centerX, centerY, ringRadius + maxBarHeight + 100, 0, Math.PI * 2);
    ctx.fill();

    const angleStep = (Math.PI * 2) / barCount;

    // Draw bars from back to front for 3D effect
    const drawOrder: number[] = [];
    for (let i = 0; i < barCount; i++) {
      const angle = i * angleStep + rotationRef.current;
      const depth = Math.sin(angle); // -1 (back) to 1 (front)
      drawOrder.push(i);
    }

    // Sort by depth (back to front)
    drawOrder.sort((a, b) => {
      const angleA = a * angleStep + rotationRef.current;
      const angleB = b * angleStep + rotationRef.current;
      return Math.sin(angleA) - Math.sin(angleB);
    });

    for (const i of drawOrder) {
      const angle = i * angleStep + rotationRef.current - Math.PI / 2;
      const dataIndex = Math.floor((i / barCount) * usableDataLength);
      const value = frequencyData[dataIndex];
      const normalizedValue = value / 255;

      // Calculate 3D depth effect
      const depth = Math.sin(i * angleStep + rotationRef.current);
      const scale = 0.5 + (depth + 1) * 0.25; // 0.5 to 1.0
      const barHeight = normalizedValue * maxBarHeight * scale;

      // Bar position on ring
      const innerX = centerX + Math.cos(angle) * ringRadius;
      const innerY = centerY + Math.sin(angle) * ringRadius;
      const outerX = centerX + Math.cos(angle) * (ringRadius + barHeight);
      const outerY = centerY + Math.sin(angle) * (ringRadius + barHeight);

      // Bar width based on depth
      const barWidth = Math.max(3, 8 * scale);

      // Color with depth-based brightness
      const brightness = 0.6 + (depth + 1) * 0.2; // 0.6 to 1.0
      let barColor: string;
      if (Array.isArray(colors)) {
        const colorIndex = Math.floor((i / barCount) * (colors.length - 1));
        barColor = colors[colorIndex];
      } else {
        barColor = colors;
      }

      // Parse and adjust brightness
      const brightnessHex = Math.floor(brightness * 255).toString(16).padStart(2, '0');

      // Draw bar shadow/glow
      if (normalizedValue > 0.3 && depth > -0.5) {
        ctx.shadowBlur = 25 * normalizedValue * scale;
        ctx.shadowColor = primaryColor;
      }

      // Create 3D gradient for bar
      const barGradient = ctx.createLinearGradient(innerX, innerY, outerX, outerY);
      if (Array.isArray(colors) && colors.length > 1) {
        barGradient.addColorStop(0, colors[0] + '80');
        barGradient.addColorStop(1, colors[colors.length - 1]);
      } else {
        barGradient.addColorStop(0, barColor + '80');
        barGradient.addColorStop(1, barColor);
      }

      // Draw main bar
      ctx.strokeStyle = barGradient;
      ctx.lineWidth = barWidth;
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(innerX, innerY);
      ctx.lineTo(outerX, outerY);
      ctx.stroke();

      ctx.shadowBlur = 0;

      // Add highlight on front-facing bars
      if (depth > 0.3 && normalizedValue > 0.5) {
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
        ctx.lineWidth = barWidth * 0.4;
        ctx.beginPath();
        ctx.moveTo(innerX, innerY);
        ctx.lineTo(outerX, outerY);
        ctx.stroke();
      }

      // Draw glowing tip for active bars in front
      if (normalizedValue > 0.6 && depth > 0) {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
        ctx.shadowBlur = 25;
        ctx.shadowColor = primaryColor;
        ctx.beginPath();
        ctx.arc(outerX, outerY, 5 * normalizedValue * scale, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
      }
    }

    // Draw inner ring
    ctx.strokeStyle = primaryColor;
    ctx.lineWidth = 4;
    ctx.shadowBlur = 30;
    ctx.shadowColor = primaryColor;
    ctx.beginPath();
    ctx.arc(centerX, centerY, ringRadius, 0, Math.PI * 2);
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Draw center orb
    const orbGradient = ctx.createRadialGradient(
      centerX - 20, centerY - 20, 0,
      centerX, centerY, 40
    );
    orbGradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
    orbGradient.addColorStop(0.3, primaryColor);
    orbGradient.addColorStop(1, primaryColor + '60');

    ctx.fillStyle = orbGradient;
    ctx.shadowBlur = 50;
    ctx.shadowColor = primaryColor;
    ctx.beginPath();
    ctx.arc(centerX, centerY, 40, 0, Math.PI * 2);
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
