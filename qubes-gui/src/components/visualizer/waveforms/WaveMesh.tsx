import React, { useEffect, useRef } from 'react';

interface WaveMeshProps {
  frequencyData: Uint8Array;
  colors: string | string[];
  width: number;
  height: number;
  frequencyRange: number;
}

export const WaveMesh: React.FC<WaveMeshProps> = ({
  frequencyData,
  colors,
  width,
  height,
  frequencyRange
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const timeRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = width;
    canvas.height = height;
    ctx.clearRect(0, 0, width, height);

    timeRef.current += 0.02;

    const cols = 32;
    const rows = 18;
    const cellWidth = width / cols;
    const cellHeight = height / rows;

    const usableDataLength = Math.floor(frequencyData.length * (frequencyRange / 100));
    const primaryColor = Array.isArray(colors) ? colors[0] : colors;

    // Create 3D perspective effect
    const perspective = height * 0.6;
    const vanishingY = height * 0.3;

    // Calculate mesh points with wave displacement
    const points: { x: number; y: number; z: number; brightness: number }[][] = [];

    for (let row = 0; row <= rows; row++) {
      points[row] = [];
      for (let col = 0; col <= cols; col++) {
        // Base position
        const baseX = col * cellWidth;
        const baseZ = row * cellHeight;

        // Get audio data for this point
        const dataIndex = Math.floor(((col + row * cols) / (rows * cols)) * usableDataLength);
        const value = frequencyData[dataIndex];
        const normalizedValue = value / 255;

        // Wave displacement with time animation
        const waveDisplacement = Math.sin(col * 0.3 + timeRef.current) *
                                 Math.cos(row * 0.3 + timeRef.current) * 20;
        const audioDisplacement = normalizedValue * 150;

        const z = baseZ;
        const y = waveDisplacement + audioDisplacement;

        // Apply 3D perspective
        const scale = perspective / (perspective + z);
        const x = (baseX - width / 2) * scale + width / 2;
        const projectedY = (y - vanishingY) * scale + vanishingY;

        // Brightness based on depth
        const brightness = 0.4 + scale * 0.6;

        points[row][col] = { x, y: projectedY, z, brightness };
      }
    }

    // Draw mesh grid from back to front
    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        const p1 = points[row][col];
        const p2 = points[row][col + 1];
        const p3 = points[row + 1][col + 1];
        const p4 = points[row + 1][col];

        const avgBrightness = (p1.brightness + p2.brightness + p3.brightness + p4.brightness) / 4;

        // Get audio intensity for this cell
        const dataIndex = Math.floor(((col + row * cols) / (rows * cols)) * usableDataLength);
        const value = frequencyData[dataIndex];
        const normalizedValue = value / 255;

        // Fill cell with gradient
        let fillColor: string;
        if (Array.isArray(colors)) {
          const colorIndex = Math.floor(normalizedValue * (colors.length - 1));
          const alpha = Math.floor(avgBrightness * normalizedValue * 180).toString(16).padStart(2, '0');
          fillColor = colors[colorIndex] + alpha;
        } else {
          const alpha = Math.floor(avgBrightness * normalizedValue * 180).toString(16).padStart(2, '0');
          fillColor = colors + alpha;
        }

        // Draw filled quad
        if (normalizedValue > 0.1) {
          ctx.fillStyle = fillColor;
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.lineTo(p3.x, p3.y);
          ctx.lineTo(p4.x, p4.y);
          ctx.closePath();
          ctx.fill();
        }

        // Draw grid lines with glow
        const lineAlpha = Math.floor(avgBrightness * 200).toString(16).padStart(2, '0');
        ctx.strokeStyle = primaryColor + lineAlpha;
        ctx.lineWidth = 1.5;

        if (normalizedValue > 0.3) {
          ctx.shadowBlur = 15 * normalizedValue;
          ctx.shadowColor = primaryColor;
        }

        // Horizontal line
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();

        // Vertical line
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p4.x, p4.y);
        ctx.stroke();

        ctx.shadowBlur = 0;

        // Add bright highlights on active cells
        if (normalizedValue > 0.7) {
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
          ctx.lineWidth = 2;
          ctx.shadowBlur = 20;
          ctx.shadowColor = 'rgba(255, 255, 255, 0.8)';
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.lineTo(p3.x, p3.y);
          ctx.lineTo(p4.x, p4.y);
          ctx.closePath();
          ctx.stroke();
          ctx.shadowBlur = 0;
        }
      }
    }

    // Draw final bottom and right edges
    for (let col = 0; col < cols; col++) {
      const p1 = points[rows][col];
      const p2 = points[rows][col + 1];
      ctx.strokeStyle = primaryColor + Math.floor(p1.brightness * 200).toString(16).padStart(2, '0');
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.stroke();
    }

    for (let row = 0; row < rows; row++) {
      const p1 = points[row][cols];
      const p2 = points[row + 1][cols];
      ctx.strokeStyle = primaryColor + Math.floor(p1.brightness * 200).toString(16).padStart(2, '0');
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.stroke();
    }

    // Draw glowing vertices for high-energy points
    for (let row = 0; row <= rows; row += 2) {
      for (let col = 0; col <= cols; col += 2) {
        const dataIndex = Math.floor(((col + row * cols) / (rows * cols)) * usableDataLength);
        const value = frequencyData[dataIndex];
        const normalizedValue = value / 255;

        if (normalizedValue > 0.6) {
          const point = points[row][col];
          ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
          ctx.shadowBlur = 20;
          ctx.shadowColor = primaryColor;
          ctx.beginPath();
          ctx.arc(point.x, point.y, 4 * normalizedValue, 0, Math.PI * 2);
          ctx.fill();
          ctx.shadowBlur = 0;
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
