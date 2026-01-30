import React, { useEffect, useRef } from 'react';

interface DotMatrixProps {
  frequencyData: Uint8Array;
  colors: string | string[];
  width: number;
  height: number;
  frequencyRange: number;
}

export const DotMatrix: React.FC<DotMatrixProps> = ({
  frequencyData,
  colors,
  width,
  height,
  frequencyRange
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(0);
  const phaseRef = useRef<number>(0);
  const prevValuesRef = useRef<number[][]>([]);

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
    const cols = 32;
    const rows = 18;

    // Initialize prev values grid
    if (prevValuesRef.current.length !== rows) {
      prevValuesRef.current = Array(rows).fill(null).map(() => Array(cols).fill(0));
    }

    const animate = () => {
      phaseRef.current += 0.03;

      const dotSpacingX = width / cols;
      const dotSpacingY = height / rows;
      const maxDotSize = Math.min(dotSpacingX, dotSpacingY) * 0.7;

      // Dark background
      const bgGrad = ctx.createRadialGradient(width / 2, height / 2, 0, width / 2, height / 2, Math.max(width, height) * 0.7);
      bgGrad.addColorStop(0, '#08081a');
      bgGrad.addColorStop(1, '#020208');
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, width, height);

      // Grid lines
      ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.04)`;
      ctx.lineWidth = 1;
      for (let x = 0; x <= cols; x++) {
        ctx.beginPath();
        ctx.moveTo(x * dotSpacingX, 0);
        ctx.lineTo(x * dotSpacingX, height);
        ctx.stroke();
      }
      for (let y = 0; y <= rows; y++) {
        ctx.beginPath();
        ctx.moveTo(0, y * dotSpacingY);
        ctx.lineTo(width, y * dotSpacingY);
        ctx.stroke();
      }

      const usableDataLength = Math.floor(frequencyData.length * (frequencyRange / 100));
      const prevValues = prevValuesRef.current;

      // First pass: calculate and smooth values
      const currentValues: number[][] = [];
      for (let row = 0; row < rows; row++) {
        currentValues[row] = [];
        for (let col = 0; col < cols; col++) {
          const dataIndex = Math.floor((col / cols) * usableDataLength);
          // Skip first 2 bins (DC offset)
          const rawValue = dataIndex < 2 ? 0 : frequencyData[dataIndex];

          // Map row position to different frequency response
          const rowFactor = 1 - Math.abs(row - rows / 2) / (rows / 2);
          const value = (rawValue / 255) * rowFactor;
          const normalizedValue = value < 0.03 ? 0 : value;

          // Smooth with previous frame
          const smoothed = prevValues[row][col] * 0.3 + normalizedValue * 0.7;
          currentValues[row][col] = smoothed;
          prevValues[row][col] = smoothed;
        }
      }

      // Draw connections first (behind dots)
      ctx.lineCap = 'round';
      for (let row = 0; row < rows; row++) {
        for (let col = 0; col < cols; col++) {
          const value = currentValues[row][col];
          if (value > 0.4) {
            const x = col * dotSpacingX + dotSpacingX / 2;
            const y = row * dotSpacingY + dotSpacingY / 2;

            // Connect to neighbors
            for (let dr = -1; dr <= 1; dr++) {
              for (let dc = -1; dc <= 1; dc++) {
                if (dr === 0 && dc === 0) continue;
                const nr = row + dr;
                const nc = col + dc;
                if (nr >= 0 && nr < rows && nc >= 0 && nc < cols) {
                  const neighborValue = currentValues[nr][nc];
                  if (neighborValue > 0.4) {
                    const nx = nc * dotSpacingX + dotSpacingX / 2;
                    const ny = nr * dotSpacingY + dotSpacingY / 2;
                    const alpha = Math.min(value, neighborValue) * 0.5;
                    ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${alpha})`;
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(x, y);
                    ctx.lineTo(nx, ny);
                    ctx.stroke();
                  }
                }
              }
            }
          }
        }
      }

      // Draw dots
      for (let row = 0; row < rows; row++) {
        for (let col = 0; col < cols; col++) {
          const value = currentValues[row][col];
          if (value < 0.02) continue;

          const x = col * dotSpacingX + dotSpacingX / 2;
          const y = row * dotSpacingY + dotSpacingY / 2;

          // Wave distortion
          const waveOffset = Math.sin(phaseRef.current + col * 0.2 + row * 0.1) * 2 * value;
          const dx = x + waveOffset;
          const dy = y + waveOffset * 0.5;

          const dotSize = value * maxDotSize;

          // Color based on intensity
          let r = rgb.r, g = rgb.g, b = rgb.b;
          if (value > 0.6) {
            r = Math.min(255, rgb.r + 60);
            g = Math.min(255, rgb.g + 60);
            b = Math.min(255, rgb.b + 60);
          }

          // Glow for active dots
          if (value > 0.3) {
            const glowGrad = ctx.createRadialGradient(dx, dy, 0, dx, dy, dotSize * 2);
            glowGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${value * 0.5})`);
            glowGrad.addColorStop(1, 'transparent');
            ctx.fillStyle = glowGrad;
            ctx.beginPath();
            ctx.arc(dx, dy, dotSize * 2, 0, Math.PI * 2);
            ctx.fill();
          }

          // Main dot with gradient
          const dotGrad = ctx.createRadialGradient(dx - dotSize * 0.2, dy - dotSize * 0.2, 0, dx, dy, dotSize);
          dotGrad.addColorStop(0, '#ffffff');
          dotGrad.addColorStop(0.4, `rgba(${r}, ${g}, ${b}, 1)`);
          dotGrad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0.8)`);
          ctx.fillStyle = dotGrad;
          ctx.beginPath();
          ctx.arc(dx, dy, dotSize / 2, 0, Math.PI * 2);
          ctx.fill();

          // Extra bright core for high values
          if (value > 0.7) {
            ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
            ctx.shadowColor = '#ffffff';
            ctx.shadowBlur = 10;
            ctx.beginPath();
            ctx.arc(dx, dy, dotSize * 0.2, 0, Math.PI * 2);
            ctx.fill();
            ctx.shadowBlur = 0;
          }
        }
      }

      // Scan line effect
      const scanY = (phaseRef.current * 30) % height;
      const scanGrad = ctx.createLinearGradient(0, scanY - 20, 0, scanY + 20);
      scanGrad.addColorStop(0, 'transparent');
      scanGrad.addColorStop(0.5, `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.08)`);
      scanGrad.addColorStop(1, 'transparent');
      ctx.fillStyle = scanGrad;
      ctx.fillRect(0, scanY - 20, width, 40);

      // Corner brackets
      ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.5)`;
      ctx.lineWidth = 2;
      const cs = 20;
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
