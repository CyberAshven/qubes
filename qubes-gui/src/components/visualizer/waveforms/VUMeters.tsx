import React, { useRef, useEffect } from 'react';

interface VUMetersProps {
  frequencyData: Uint8Array;
  colors: string | string[];
  width: number;
  height: number;
  frequencyRange: number;
}

export const VUMeters: React.FC<VUMetersProps> = ({
  frequencyData,
  colors,
  width,
  height,
  frequencyRange
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(0);
  const needleAnglesRef = useRef<number[]>([0, 0]);
  const needleTrailsRef = useRef<number[][]>([[], []]);
  const peakHoldRef = useRef<number[]>([0, 0]);
  const peakDecayRef = useRef<number[]>([0, 0]);
  const timeRef = useRef<number>(0);
  const scanLineRef = useRef<number>(0);

  // Get colors
  const getColors = (): { primary: string; secondary: string; accent: string } => {
    if (Array.isArray(colors) && colors.length > 0) {
      return {
        primary: colors[0],
        secondary: colors[1] || '#ff00ff',
        accent: colors[2] || '#00ffff'
      };
    }
    const color = typeof colors === 'string' ? colors : '#00ffff';
    return { primary: color, secondary: '#ff00ff', accent: '#00ffff' };
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { primary, secondary, accent } = getColors();

    // Parse colors to RGB
    const parseHex = (hex: string) => {
      const h = hex.replace('#', '');
      return {
        r: parseInt(h.substr(0, 2), 16),
        g: parseInt(h.substr(2, 2), 16),
        b: parseInt(h.substr(4, 2), 16)
      };
    };

    const primaryRGB = parseHex(primary);
    const secondaryRGB = parseHex(secondary);

    const drawCyberpunkMeter = (
      centerX: number,
      centerY: number,
      radius: number,
      value: number,
      peakValue: number,
      label: string,
      isLeft: boolean,
      time: number
    ) => {
      const minAngle = Math.PI * 1.15;
      const maxAngle = Math.PI * -0.15;
      const needleAngle = minAngle + (maxAngle - minAngle) * value;
      const peakAngle = minAngle + (maxAngle - minAngle) * peakValue;

      // Outer hexagonal frame glow
      ctx.save();
      ctx.translate(centerX, centerY);

      // Pulsing outer ring
      const pulse = 0.8 + Math.sin(time * 3) * 0.2 * value;

      // Multiple glowing arc layers
      for (let layer = 3; layer >= 0; layer--) {
        const layerRadius = radius + layer * 8;
        const alpha = (0.3 - layer * 0.08) * pulse;

        ctx.beginPath();
        ctx.arc(0, 0, layerRadius, minAngle, maxAngle, true);
        ctx.strokeStyle = `rgba(${primaryRGB.r}, ${primaryRGB.g}, ${primaryRGB.b}, ${alpha})`;
        ctx.lineWidth = 4 - layer;
        ctx.lineCap = 'round';
        ctx.stroke();
      }

      // Main arc background (dark)
      ctx.beginPath();
      ctx.arc(0, 0, radius, minAngle, maxAngle, true);
      ctx.strokeStyle = 'rgba(20, 20, 40, 0.8)';
      ctx.lineWidth = 25;
      ctx.stroke();

      // Segmented level indicators
      const segments = 20;
      const segmentGap = 0.02;

      for (let i = 0; i < segments; i++) {
        const segmentStart = minAngle + (maxAngle - minAngle) * (i / segments) + segmentGap;
        const segmentEnd = minAngle + (maxAngle - minAngle) * ((i + 1) / segments) - segmentGap;
        const segmentValue = i / segments;
        const isActive = segmentValue <= value;
        const isPeak = Math.abs(segmentValue - peakValue) < 0.06;

        // Color gradient from primary to red in danger zone
        let r, g, b;
        if (segmentValue < 0.6) {
          // Primary color zone
          r = primaryRGB.r;
          g = primaryRGB.g;
          b = primaryRGB.b;
        } else if (segmentValue < 0.8) {
          // Transition to yellow/orange
          const t = (segmentValue - 0.6) / 0.2;
          r = Math.floor(primaryRGB.r + (255 - primaryRGB.r) * t);
          g = Math.floor(primaryRGB.g + (200 - primaryRGB.g) * t);
          b = Math.floor(primaryRGB.b * (1 - t));
        } else {
          // Red danger zone
          r = 255;
          g = 50;
          b = 50;
        }

        if (isActive) {
          // Glowing active segment
          ctx.beginPath();
          ctx.arc(0, 0, radius, segmentStart, segmentEnd, true);

          // Outer glow
          ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.5)`;
          ctx.lineWidth = 30;
          ctx.stroke();

          // Main segment
          ctx.beginPath();
          ctx.arc(0, 0, radius, segmentStart, segmentEnd, true);
          ctx.strokeStyle = `rgb(${r}, ${g}, ${b})`;
          ctx.lineWidth = 20;
          ctx.stroke();

          // Inner bright core
          ctx.beginPath();
          ctx.arc(0, 0, radius, segmentStart, segmentEnd, true);
          ctx.strokeStyle = `rgba(255, 255, 255, 0.8)`;
          ctx.lineWidth = 8;
          ctx.stroke();
        } else {
          // Dim inactive segment
          ctx.beginPath();
          ctx.arc(0, 0, radius, segmentStart, segmentEnd, true);
          ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.15)`;
          ctx.lineWidth = 20;
          ctx.stroke();
        }

        // Peak hold indicator
        if (isPeak && peakValue > 0.05) {
          ctx.beginPath();
          ctx.arc(0, 0, radius, segmentStart, segmentEnd, true);
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 22;
          ctx.stroke();

          // Peak glow
          ctx.beginPath();
          ctx.arc(0, 0, radius, segmentStart, segmentEnd, true);
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
          ctx.lineWidth = 30;
          ctx.stroke();
        }
      }

      // Digital scale markers
      ctx.font = `bold ${radius * 0.12}px 'Courier New', monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      const markers = [
        { pos: 0, label: '-20' },
        { pos: 0.3, label: '-10' },
        { pos: 0.5, label: '-5' },
        { pos: 0.65, label: '0' },
        { pos: 0.8, label: '+5' },
        { pos: 1, label: '+10' }
      ];

      markers.forEach(marker => {
        const angle = minAngle + (maxAngle - minAngle) * marker.pos;
        const labelRadius = radius + 35;
        const x = Math.cos(angle) * labelRadius;
        const y = Math.sin(angle) * labelRadius;

        const isInDanger = marker.pos >= 0.65;
        ctx.fillStyle = isInDanger ? '#ff4444' : `rgba(${primaryRGB.r}, ${primaryRGB.g}, ${primaryRGB.b}, 0.9)`;
        ctx.fillText(marker.label, x, y);
      });

      // Glowing needle with trail
      const needleLength = radius * 0.95;
      const trailIndex = isLeft ? 0 : 1;
      const trail = needleTrailsRef.current[trailIndex];

      // Store current angle in trail
      trail.push(needleAngle);
      if (trail.length > 8) trail.shift();

      // Draw needle trail (motion blur effect)
      trail.forEach((trailAngle, i) => {
        const alpha = (i / trail.length) * 0.3;
        const trailWidth = 2 + (i / trail.length) * 2;

        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(
          Math.cos(trailAngle) * needleLength,
          Math.sin(trailAngle) * needleLength
        );
        ctx.strokeStyle = `rgba(${primaryRGB.r}, ${primaryRGB.g}, ${primaryRGB.b}, ${alpha})`;
        ctx.lineWidth = trailWidth;
        ctx.lineCap = 'round';
        ctx.stroke();
      });

      // Main needle glow
      for (let glow = 3; glow >= 0; glow--) {
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(
          Math.cos(needleAngle) * needleLength,
          Math.sin(needleAngle) * needleLength
        );

        const glowAlpha = 0.4 - glow * 0.1;
        ctx.strokeStyle = `rgba(${primaryRGB.r}, ${primaryRGB.g}, ${primaryRGB.b}, ${glowAlpha})`;
        ctx.lineWidth = 12 - glow * 2;
        ctx.lineCap = 'round';
        ctx.stroke();
      }

      // Needle core (bright white)
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.lineTo(
        Math.cos(needleAngle) * needleLength,
        Math.sin(needleAngle) * needleLength
      );
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 3;
      ctx.lineCap = 'round';
      ctx.stroke();

      // Needle tip glow ball
      const tipX = Math.cos(needleAngle) * needleLength;
      const tipY = Math.sin(needleAngle) * needleLength;

      const tipGlow = ctx.createRadialGradient(tipX, tipY, 0, tipX, tipY, 15);
      tipGlow.addColorStop(0, '#ffffff');
      tipGlow.addColorStop(0.3, `rgba(${primaryRGB.r}, ${primaryRGB.g}, ${primaryRGB.b}, 0.8)`);
      tipGlow.addColorStop(1, 'transparent');

      ctx.beginPath();
      ctx.arc(tipX, tipY, 15, 0, Math.PI * 2);
      ctx.fillStyle = tipGlow;
      ctx.fill();

      // Center pivot - holographic style
      const pivotGlow = ctx.createRadialGradient(0, 0, 0, 0, 0, 25);
      pivotGlow.addColorStop(0, `rgba(${primaryRGB.r}, ${primaryRGB.g}, ${primaryRGB.b}, 0.9)`);
      pivotGlow.addColorStop(0.5, `rgba(${primaryRGB.r}, ${primaryRGB.g}, ${primaryRGB.b}, 0.4)`);
      pivotGlow.addColorStop(1, 'transparent');

      ctx.beginPath();
      ctx.arc(0, 0, 25, 0, Math.PI * 2);
      ctx.fillStyle = pivotGlow;
      ctx.fill();

      // Center ring
      ctx.beginPath();
      ctx.arc(0, 0, 12, 0, Math.PI * 2);
      ctx.strokeStyle = primary;
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(0, 0, 8, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.fill();

      // Channel label with glow
      ctx.font = `bold ${radius * 0.25}px 'Courier New', monospace`;
      ctx.textAlign = 'center';

      // Label glow
      ctx.shadowColor = primary;
      ctx.shadowBlur = 20;
      ctx.fillStyle = primary;
      ctx.fillText(label, 0, radius * 0.5);
      ctx.shadowBlur = 0;

      // dB readout
      const dbValue = value > 0 ? Math.round(-20 + value * 30) : -60;
      ctx.font = `bold ${radius * 0.15}px 'Courier New', monospace`;
      ctx.fillStyle = value > 0.7 ? '#ff4444' : primary;
      ctx.shadowColor = ctx.fillStyle;
      ctx.shadowBlur = 10;
      ctx.fillText(`${dbValue > 0 ? '+' : ''}${dbValue} dB`, 0, radius * 0.7);
      ctx.shadowBlur = 0;

      // Peak LED
      const ledY = -radius - 20;
      const ledOn = peakValue > 0.7;

      if (ledOn) {
        // LED glow
        const ledGlow = ctx.createRadialGradient(0, ledY, 0, 0, ledY, 20);
        ledGlow.addColorStop(0, '#ff0000');
        ledGlow.addColorStop(0.5, 'rgba(255, 0, 0, 0.5)');
        ledGlow.addColorStop(1, 'transparent');
        ctx.fillStyle = ledGlow;
        ctx.fillRect(-20, ledY - 20, 40, 40);
      }

      ctx.beginPath();
      ctx.arc(0, ledY, 6, 0, Math.PI * 2);
      ctx.fillStyle = ledOn ? '#ff3333' : '#331111';
      ctx.fill();
      ctx.strokeStyle = ledOn ? '#ff6666' : '#222';
      ctx.lineWidth = 2;
      ctx.stroke();

      // "PEAK" label
      ctx.font = `bold ${radius * 0.08}px 'Courier New', monospace`;
      ctx.fillStyle = ledOn ? '#ff4444' : '#444';
      ctx.fillText('PEAK', 0, ledY + 20);

      ctx.restore();
    };

    const animate = () => {
      timeRef.current += 0.016;
      scanLineRef.current = (scanLineRef.current + 2) % height;

      // Calculate audio levels
      const dataLength = Math.floor(frequencyData.length * (frequencyRange / 100));
      let leftSum = 0;
      let rightSum = 0;
      const halfLength = Math.floor(dataLength / 2);

      for (let i = 0; i < halfLength; i++) {
        leftSum += frequencyData[i];
      }
      for (let i = halfLength; i < dataLength; i++) {
        rightSum += frequencyData[i];
      }

      const leftLevel = halfLength > 0 ? leftSum / halfLength / 255 : 0;
      const rightLevel = (dataLength - halfLength) > 0 ? rightSum / (dataLength - halfLength) / 255 : 0;

      // Smooth needle movement
      const attack = 0.2;
      const release = 0.08;

      for (let i = 0; i < 2; i++) {
        const target = i === 0 ? leftLevel : rightLevel;
        if (target > needleAnglesRef.current[i]) {
          needleAnglesRef.current[i] += (target - needleAnglesRef.current[i]) * attack;
        } else {
          needleAnglesRef.current[i] -= release;
        }
        needleAnglesRef.current[i] = Math.max(0, Math.min(1, needleAnglesRef.current[i]));

        // Peak hold
        if (needleAnglesRef.current[i] > peakHoldRef.current[i]) {
          peakHoldRef.current[i] = needleAnglesRef.current[i];
          peakDecayRef.current[i] = 45;
        } else if (peakDecayRef.current[i] > 0) {
          peakDecayRef.current[i]--;
        } else {
          peakHoldRef.current[i] -= 0.015;
          peakHoldRef.current[i] = Math.max(0, peakHoldRef.current[i]);
        }
      }

      // Clear with dark gradient
      const bgGradient = ctx.createLinearGradient(0, 0, 0, height);
      bgGradient.addColorStop(0, '#0a0a15');
      bgGradient.addColorStop(0.5, '#05051a');
      bgGradient.addColorStop(1, '#0a0a15');
      ctx.fillStyle = bgGradient;
      ctx.fillRect(0, 0, width, height);

      // Grid lines (subtle)
      ctx.strokeStyle = 'rgba(100, 100, 150, 0.1)';
      ctx.lineWidth = 1;
      const gridSize = 40;
      for (let x = 0; x < width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Scan line effect
      const scanGradient = ctx.createLinearGradient(0, scanLineRef.current - 50, 0, scanLineRef.current + 50);
      scanGradient.addColorStop(0, 'transparent');
      scanGradient.addColorStop(0.5, `rgba(${primaryRGB.r}, ${primaryRGB.g}, ${primaryRGB.b}, 0.05)`);
      scanGradient.addColorStop(1, 'transparent');
      ctx.fillStyle = scanGradient;
      ctx.fillRect(0, 0, width, height);

      // Calculate meter positions
      const meterRadius = Math.min(width * 0.22, height * 0.35);
      const spacing = width * 0.1;
      const totalWidth = meterRadius * 4 + spacing;
      const startX = (width - totalWidth) / 2 + meterRadius;
      const meterY = height * 0.55;

      // Draw meters
      drawCyberpunkMeter(
        startX,
        meterY,
        meterRadius,
        needleAnglesRef.current[0],
        peakHoldRef.current[0],
        'L',
        true,
        timeRef.current
      );

      drawCyberpunkMeter(
        startX + meterRadius * 2 + spacing,
        meterY,
        meterRadius,
        needleAnglesRef.current[1],
        peakHoldRef.current[1],
        'R',
        false,
        timeRef.current
      );

      // Title
      ctx.font = `bold ${Math.min(width, height) * 0.05}px 'Courier New', monospace`;
      ctx.textAlign = 'center';
      ctx.fillStyle = primary;
      ctx.shadowColor = primary;
      ctx.shadowBlur = 20;
      ctx.fillText('// AUDIO LEVEL //', width / 2, height * 0.12);
      ctx.shadowBlur = 0;

      // Decorative corner elements
      const cornerSize = 30;
      ctx.strokeStyle = `rgba(${primaryRGB.r}, ${primaryRGB.g}, ${primaryRGB.b}, 0.5)`;
      ctx.lineWidth = 2;

      // Top left
      ctx.beginPath();
      ctx.moveTo(20, 20 + cornerSize);
      ctx.lineTo(20, 20);
      ctx.lineTo(20 + cornerSize, 20);
      ctx.stroke();

      // Top right
      ctx.beginPath();
      ctx.moveTo(width - 20 - cornerSize, 20);
      ctx.lineTo(width - 20, 20);
      ctx.lineTo(width - 20, 20 + cornerSize);
      ctx.stroke();

      // Bottom left
      ctx.beginPath();
      ctx.moveTo(20, height - 20 - cornerSize);
      ctx.lineTo(20, height - 20);
      ctx.lineTo(20 + cornerSize, height - 20);
      ctx.stroke();

      // Bottom right
      ctx.beginPath();
      ctx.moveTo(width - 20 - cornerSize, height - 20);
      ctx.lineTo(width - 20, height - 20);
      ctx.lineTo(width - 20, height - 20 - cornerSize);
      ctx.stroke();

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
