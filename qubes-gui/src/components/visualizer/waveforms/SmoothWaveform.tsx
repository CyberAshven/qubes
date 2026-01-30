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
  const animationRef = useRef<number>(0);
  const phaseRef = useRef<number>(0);
  const historyRef = useRef<number[][]>([]);

  const getColor = () => {
    if (Array.isArray(colors) && colors.length > 0) return colors[0];
    return typeof colors === 'string' ? colors : '#00ff88';
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

    const animate = () => {
      phaseRef.current += 0.02;
      const centerY = height / 2;

      // Background with slight gradient
      const bgGrad = ctx.createRadialGradient(width / 2, height / 2, 0, width / 2, height / 2, Math.max(width, height) * 0.7);
      bgGrad.addColorStop(0, '#0a0a15');
      bgGrad.addColorStop(1, '#030308');
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, width, height);

      // Horizontal guide lines
      ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.05)`;
      ctx.lineWidth = 1;
      for (let y = height * 0.25; y <= height * 0.75; y += height * 0.25) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      const usableDataLength = Math.floor(frequencyData.length * (frequencyRange / 100));
      const sampleCount = 128;

      // Build current wave
      const currentWave: number[] = [];
      for (let i = 0; i < sampleCount; i++) {
        const dataIndex = Math.floor((i / sampleCount) * usableDataLength);
        const value = dataIndex < 2 ? 0 : frequencyData[dataIndex];
        const normalizedValue = value / 255 < 0.03 ? 0 : value / 255;
        currentWave.push(normalizedValue);
      }

      // Store in history for trail effect
      historyRef.current.unshift(currentWave);
      if (historyRef.current.length > 5) historyRef.current.pop();

      // Draw history trails
      historyRef.current.forEach((wave, histIndex) => {
        if (histIndex === 0) return; // Skip current, draw it last
        const alpha = (1 - histIndex / historyRef.current.length) * 0.2;

        ctx.beginPath();
        ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${alpha})`;
        ctx.lineWidth = 3 - histIndex * 0.5;

        for (let i = 0; i < wave.length; i++) {
          const x = (i / wave.length) * width;
          const amplitude = wave[i] * (height * 0.35);
          const y = centerY + Math.sin((i / wave.length) * Math.PI * 4 + phaseRef.current - histIndex * 0.2) * amplitude;

          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      });

      // Draw main wave with glow
      const wave = currentWave;

      // Glow layers
      for (let glow = 3; glow >= 0; glow--) {
        ctx.beginPath();
        ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${0.15 - glow * 0.04})`;
        ctx.lineWidth = 10 + glow * 6;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        for (let i = 0; i < wave.length; i++) {
          const x = (i / wave.length) * width;
          const amplitude = wave[i] * (height * 0.35);
          const y = centerY + Math.sin((i / wave.length) * Math.PI * 4 + phaseRef.current) * amplitude;

          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }

      // Main bright wave
      ctx.beginPath();
      const waveGrad = ctx.createLinearGradient(0, 0, width, 0);
      waveGrad.addColorStop(0, primaryColor);
      waveGrad.addColorStop(0.5, `rgba(${Math.min(255, rgb.r + 80)}, ${Math.min(255, rgb.g + 80)}, ${Math.min(255, rgb.b + 80)}, 1)`);
      waveGrad.addColorStop(1, primaryColor);
      ctx.strokeStyle = waveGrad;
      ctx.lineWidth = 4;

      for (let i = 0; i < wave.length; i++) {
        const x = (i / wave.length) * width;
        const amplitude = wave[i] * (height * 0.35);
        const y = centerY + Math.sin((i / wave.length) * Math.PI * 4 + phaseRef.current) * amplitude;

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // White core
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.7)';
      ctx.lineWidth = 1.5;

      for (let i = 0; i < wave.length; i++) {
        const x = (i / wave.length) * width;
        const amplitude = wave[i] * (height * 0.35);
        const y = centerY + Math.sin((i / wave.length) * Math.PI * 4 + phaseRef.current) * amplitude;

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Particles at peaks
      for (let i = 0; i < wave.length; i += 6) {
        if (wave[i] > 0.4) {
          const x = (i / wave.length) * width;
          const amplitude = wave[i] * (height * 0.35);
          const y = centerY + Math.sin((i / wave.length) * Math.PI * 4 + phaseRef.current) * amplitude;

          const particleGrad = ctx.createRadialGradient(x, y, 0, x, y, 8 * wave[i]);
          particleGrad.addColorStop(0, '#ffffff');
          particleGrad.addColorStop(0.3, primaryColor);
          particleGrad.addColorStop(1, 'transparent');
          ctx.fillStyle = particleGrad;
          ctx.beginPath();
          ctx.arc(x, y, 8 * wave[i], 0, Math.PI * 2);
          ctx.fill();
        }
      }

      // Corner brackets
      ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.4)`;
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
