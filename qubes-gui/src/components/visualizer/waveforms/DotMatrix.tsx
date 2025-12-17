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

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = width;
    canvas.height = height;
    ctx.clearRect(0, 0, width, height);

    const cols = 48;
    const rows = 28;
    const dotSpacingX = width / cols;
    const dotSpacingY = height / rows;
    const maxDotSize = Math.min(dotSpacingX, dotSpacingY) * 0.8;

    const usableDataLength = Math.floor(frequencyData.length * (frequencyRange / 100));
    const primaryColor = Array.isArray(colors) ? colors[0] : colors;

    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        const x = col * dotSpacingX + dotSpacingX / 2;
        const y = row * dotSpacingY + dotSpacingY / 2;

        // Map position to frequency data
        const dataIndex = Math.floor(((col + row * cols) / (rows * cols)) * usableDataLength);
        const value = frequencyData[dataIndex];
        const normalizedValue = value / 255;

        // Add wave effect based on position
        const distanceFromCenter = Math.sqrt(
          Math.pow((col - cols / 2) / (cols / 2), 2) +
          Math.pow((row - rows / 2) / (rows / 2), 2)
        );

        const waveEffect = Math.sin(distanceFromCenter * Math.PI * 2 + Date.now() / 500) * 0.2 + 0.8;
        const dotSize = normalizedValue * maxDotSize * waveEffect;

        if (dotSize > 2) {
          // Draw glow
          if (normalizedValue > 0.4) {
            ctx.shadowBlur = 25 * normalizedValue;
            ctx.shadowColor = primaryColor;
          }

          // Color based on intensity and position
          let dotColor: string | CanvasGradient;
          if (Array.isArray(colors)) {
            const colorIndex = Math.floor((normalizedValue * (colors.length - 1)));
            dotColor = colors[colorIndex];
          } else {
            const alpha = Math.floor(normalizedValue * 255).toString(16).padStart(2, '0');
            dotColor = colors + alpha;
          }

          ctx.fillStyle = dotColor;
          ctx.beginPath();
          ctx.arc(x, y, dotSize / 2, 0, Math.PI * 2);
          ctx.fill();

          ctx.shadowBlur = 0;

          // Add bright center for active dots
          if (normalizedValue > 0.7) {
            ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
            ctx.beginPath();
            ctx.arc(x, y, (dotSize / 2) * 0.4, 0, Math.PI * 2);
            ctx.fill();
          }

          // Draw connection lines to nearby dots
          if (normalizedValue > 0.6) {
            const searchRadius = dotSpacingX * 1.5;
            for (let nearRow = Math.max(0, row - 1); nearRow <= Math.min(rows - 1, row + 1); nearRow++) {
              for (let nearCol = Math.max(0, col - 1); nearCol <= Math.min(cols - 1, col + 1); nearCol++) {
                if (nearRow === row && nearCol === col) continue;

                const nearX = nearCol * dotSpacingX + dotSpacingX / 2;
                const nearY = nearRow * dotSpacingY + dotSpacingY / 2;
                const nearDataIndex = Math.floor(((nearCol + nearRow * cols) / (rows * cols)) * usableDataLength);
                const nearValue = frequencyData[nearDataIndex];
                const nearNormalizedValue = nearValue / 255;

                if (nearNormalizedValue > 0.6) {
                  const distance = Math.sqrt(Math.pow(nearX - x, 2) + Math.pow(nearY - y, 2));
                  if (distance < searchRadius) {
                    ctx.strokeStyle = primaryColor + '40';
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(x, y);
                    ctx.lineTo(nearX, nearY);
                    ctx.stroke();
                  }
                }
              }
            }
          }
        }
      }
    }
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
