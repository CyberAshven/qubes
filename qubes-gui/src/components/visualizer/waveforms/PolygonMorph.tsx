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
  const animationRef = useRef<number>(0);
  const rotationRef = useRef<number>(0);
  const trailRef = useRef<{ x: number; y: number; value: number }[][]>([]);

  const getColor = () => {
    if (Array.isArray(colors) && colors.length > 0) return colors[0];
    return typeof colors === 'string' ? colors : '#ff6600';
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
    const sides = 48;

    const animate = () => {
      rotationRef.current += 0.008;

      const centerX = width / 2;
      const centerY = height / 2;
      const baseRadius = Math.min(width, height) * 0.22;

      // Dark background with subtle radial gradient
      const bgGrad = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, Math.max(width, height) * 0.8);
      bgGrad.addColorStop(0, '#0c0c18');
      bgGrad.addColorStop(0.5, '#060610');
      bgGrad.addColorStop(1, '#020205');
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, width, height);

      // Hexagonal grid pattern
      ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.04)`;
      ctx.lineWidth = 1;
      const gridSize = 40;
      for (let x = -gridSize; x < width + gridSize; x += gridSize * 1.5) {
        for (let y = -gridSize; y < height + gridSize; y += gridSize * 0.866) {
          const offset = (Math.floor(y / (gridSize * 0.866)) % 2) * gridSize * 0.75;
          ctx.beginPath();
          for (let i = 0; i < 6; i++) {
            const angle = (i / 6) * Math.PI * 2;
            const px = x + offset + Math.cos(angle) * (gridSize / 2);
            const py = y + Math.sin(angle) * (gridSize / 2);
            if (i === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
          }
          ctx.closePath();
          ctx.stroke();
        }
      }

      const usableDataLength = Math.floor(frequencyData.length * (frequencyRange / 100));

      // Calculate polygon points
      const points: { x: number; y: number; value: number }[] = [];
      for (let i = 0; i < sides; i++) {
        const angle = (i / sides) * Math.PI * 2 + rotationRef.current;
        const dataIndex = Math.floor((i / sides) * usableDataLength);
        // Skip first 3 bins (DC offset)
        const rawValue = dataIndex < 3 ? 0 : frequencyData[dataIndex];
        const normalizedValue = rawValue / 255 < 0.03 ? 0 : rawValue / 255;

        const morphedRadius = baseRadius + (normalizedValue * baseRadius * 0.8);
        const x = centerX + Math.cos(angle) * morphedRadius;
        const y = centerY + Math.sin(angle) * morphedRadius;

        points.push({ x, y, value: normalizedValue });
      }

      // Store trail
      trailRef.current.unshift([...points]);
      if (trailRef.current.length > 6) trailRef.current.pop();

      // Draw outer glow rings
      for (let ring = 4; ring >= 0; ring--) {
        const ringRadius = baseRadius * 1.6 + ring * 25;
        const ringGrad = ctx.createRadialGradient(centerX, centerY, ringRadius - 30, centerX, centerY, ringRadius);
        ringGrad.addColorStop(0, 'transparent');
        ringGrad.addColorStop(1, `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${0.03 / (ring + 1)})`);
        ctx.fillStyle = ringGrad;
        ctx.beginPath();
        ctx.arc(centerX, centerY, ringRadius, 0, Math.PI * 2);
        ctx.fill();
      }

      // Draw trail polygons
      trailRef.current.forEach((trailPoints, trailIndex) => {
        if (trailIndex === 0) return;
        const alpha = (1 - trailIndex / trailRef.current.length) * 0.15;

        ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${alpha})`;
        ctx.lineWidth = 3 - trailIndex * 0.4;
        ctx.beginPath();
        ctx.moveTo(trailPoints[0].x, trailPoints[0].y);
        for (let i = 1; i <= trailPoints.length; i++) {
          const curr = trailPoints[i % trailPoints.length];
          const next = trailPoints[(i + 1) % trailPoints.length];
          const xc = (curr.x + next.x) / 2;
          const yc = (curr.y + next.y) / 2;
          ctx.quadraticCurveTo(curr.x, curr.y, xc, yc);
        }
        ctx.closePath();
        ctx.stroke();
      });

      // Draw filled polygon with gradient
      const fillGrad = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, baseRadius * 1.8);
      fillGrad.addColorStop(0, `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.4)`);
      fillGrad.addColorStop(0.5, `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.15)`);
      fillGrad.addColorStop(1, `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.05)`);
      ctx.fillStyle = fillGrad;
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      for (let i = 1; i <= points.length; i++) {
        const curr = points[i % points.length];
        const next = points[(i + 1) % points.length];
        const xc = (curr.x + next.x) / 2;
        const yc = (curr.y + next.y) / 2;
        ctx.quadraticCurveTo(curr.x, curr.y, xc, yc);
      }
      ctx.closePath();
      ctx.fill();

      // Glow layers for outline
      for (let glow = 3; glow >= 0; glow--) {
        ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${0.15 - glow * 0.04})`;
        ctx.lineWidth = 8 + glow * 5;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.beginPath();
        ctx.moveTo(points[0].x, points[0].y);
        for (let i = 1; i <= points.length; i++) {
          const curr = points[i % points.length];
          const next = points[(i + 1) % points.length];
          const xc = (curr.x + next.x) / 2;
          const yc = (curr.y + next.y) / 2;
          ctx.quadraticCurveTo(curr.x, curr.y, xc, yc);
        }
        ctx.closePath();
        ctx.stroke();
      }

      // Main bright outline
      ctx.strokeStyle = primaryColor;
      ctx.lineWidth = 3;
      ctx.shadowColor = primaryColor;
      ctx.shadowBlur = 20;
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      for (let i = 1; i <= points.length; i++) {
        const curr = points[i % points.length];
        const next = points[(i + 1) % points.length];
        const xc = (curr.x + next.x) / 2;
        const yc = (curr.y + next.y) / 2;
        ctx.quadraticCurveTo(curr.x, curr.y, xc, yc);
      }
      ctx.closePath();
      ctx.stroke();
      ctx.shadowBlur = 0;

      // White highlight outline
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      for (let i = 1; i <= points.length; i++) {
        const curr = points[i % points.length];
        const next = points[(i + 1) % points.length];
        const xc = (curr.x + next.x) / 2;
        const yc = (curr.y + next.y) / 2;
        ctx.quadraticCurveTo(curr.x, curr.y, xc, yc);
      }
      ctx.closePath();
      ctx.stroke();

      // Vertex particles for high-energy points
      for (let i = 0; i < points.length; i += 3) {
        const point = points[i];
        if (point.value > 0.5) {
          // Outer glow
          const particleGrad = ctx.createRadialGradient(point.x, point.y, 0, point.x, point.y, 12 * point.value);
          particleGrad.addColorStop(0, '#ffffff');
          particleGrad.addColorStop(0.3, primaryColor);
          particleGrad.addColorStop(1, 'transparent');
          ctx.fillStyle = particleGrad;
          ctx.beginPath();
          ctx.arc(point.x, point.y, 12 * point.value, 0, Math.PI * 2);
          ctx.fill();

          // Bright core
          ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
          ctx.beginPath();
          ctx.arc(point.x, point.y, 3 * point.value, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      // Center orb
      let totalIntensity = 0;
      for (let i = 3; i < usableDataLength; i++) {
        totalIntensity += frequencyData[i];
      }
      const avgIntensity = usableDataLength > 3 ? totalIntensity / (usableDataLength - 3) / 255 : 0;

      const orbRadius = baseRadius * 0.25 + avgIntensity * baseRadius * 0.1;

      // Orb glow
      const orbGlow = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, orbRadius * 2);
      orbGlow.addColorStop(0, `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${0.4 + avgIntensity * 0.3})`);
      orbGlow.addColorStop(1, 'transparent');
      ctx.fillStyle = orbGlow;
      ctx.beginPath();
      ctx.arc(centerX, centerY, orbRadius * 2, 0, Math.PI * 2);
      ctx.fill();

      // Main orb
      const orbGrad = ctx.createRadialGradient(centerX - orbRadius * 0.3, centerY - orbRadius * 0.3, 0, centerX, centerY, orbRadius);
      orbGrad.addColorStop(0, '#ffffff');
      orbGrad.addColorStop(0.4, primaryColor);
      orbGrad.addColorStop(1, `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.7)`);
      ctx.fillStyle = orbGrad;
      ctx.shadowColor = primaryColor;
      ctx.shadowBlur = 30;
      ctx.beginPath();
      ctx.arc(centerX, centerY, orbRadius, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;

      // Orb ring
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.7)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(centerX, centerY, orbRadius, 0, Math.PI * 2);
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
