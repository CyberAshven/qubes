import React, { useEffect, useRef } from 'react';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  dataIndex: number;
  hue: number;
}

interface ParticleFieldProps {
  frequencyData: Uint8Array;
  colors: string | string[];
  width: number;
  height: number;
  frequencyRange: number;
}

export const ParticleField: React.FC<ParticleFieldProps> = ({
  frequencyData,
  colors,
  width,
  height,
  frequencyRange
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);

  // Initialize particles once
  useEffect(() => {
    const particleCount = 300;
    particlesRef.current = [];

    for (let i = 0; i < particleCount; i++) {
      particlesRef.current.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 2,
        vy: (Math.random() - 0.5) * 2,
        size: Math.random() * 3 + 2,
        dataIndex: Math.floor(Math.random() * 256),
        hue: Math.random() * 360
      });
    }
  }, [width, height]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = width;
    canvas.height = height;

    // Fade previous frame for trail effect
    ctx.fillStyle = 'rgba(0, 0, 0, 0.15)';
    ctx.fillRect(0, 0, width, height);

    const usableDataLength = Math.floor(frequencyData.length * (frequencyRange / 100));
    const primaryColor = Array.isArray(colors) ? colors[0] : colors;

    const particles = particlesRef.current;

    // Update and draw particles
    for (let i = 0; i < particles.length; i++) {
      const particle = particles[i];

      // Get audio data for this particle
      const dataIndex = particle.dataIndex % usableDataLength;
      const value = frequencyData[dataIndex];
      const normalizedValue = value / 255;

      // Physics - particles are attracted to center when audio is active
      const centerX = width / 2;
      const centerY = height / 2;
      const dx = centerX - particle.x;
      const dy = centerY - particle.y;
      const distance = Math.sqrt(dx * dx + dy * dy);

      // Audio-reactive force
      const force = normalizedValue * 0.5;
      particle.vx += (dx / distance) * force;
      particle.vy += (dy / distance) * force;

      // Add some randomness
      particle.vx += (Math.random() - 0.5) * 0.2;
      particle.vy += (Math.random() - 0.5) * 0.2;

      // Damping
      particle.vx *= 0.98;
      particle.vy *= 0.98;

      // Update position
      particle.x += particle.vx;
      particle.y += particle.vy;

      // Wrap around edges
      if (particle.x < 0) particle.x = width;
      if (particle.x > width) particle.x = 0;
      if (particle.y < 0) particle.y = height;
      if (particle.y > height) particle.y = 0;

      // Audio-reactive size
      const reactiveSize = particle.size + normalizedValue * 8;

      // Draw particle with glow
      if (normalizedValue > 0.2) {
        ctx.shadowBlur = 20 * normalizedValue;
        ctx.shadowColor = primaryColor;
      }

      // Color based on audio intensity and particle properties
      let particleColor: string;
      if (Array.isArray(colors)) {
        const colorIndex = Math.floor(normalizedValue * (colors.length - 1));
        particleColor = colors[colorIndex];
      } else {
        const alpha = Math.floor((0.5 + normalizedValue * 0.5) * 255).toString(16).padStart(2, '0');
        particleColor = colors + alpha;
      }

      ctx.fillStyle = particleColor;
      ctx.beginPath();
      ctx.arc(particle.x, particle.y, reactiveSize, 0, Math.PI * 2);
      ctx.fill();

      ctx.shadowBlur = 0;

      // Draw bright core for high-energy particles
      if (normalizedValue > 0.7) {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, reactiveSize * 0.4, 0, Math.PI * 2);
        ctx.fill();
      }

      // Draw connections between nearby particles
      if (normalizedValue > 0.5) {
        for (let j = i + 1; j < particles.length; j++) {
          const other = particles[j];
          const pdx = other.x - particle.x;
          const pdy = other.y - particle.y;
          const pdist = Math.sqrt(pdx * pdx + pdy * pdy);

          if (pdist < 100) {
            const otherDataIndex = other.dataIndex % usableDataLength;
            const otherValue = frequencyData[otherDataIndex];
            const otherNormalizedValue = otherValue / 255;

            if (otherNormalizedValue > 0.5) {
              const alpha = Math.floor((1 - pdist / 100) * normalizedValue * 100).toString(16).padStart(2, '0');
              ctx.strokeStyle = primaryColor + alpha;
              ctx.lineWidth = 1;
              ctx.beginPath();
              ctx.moveTo(particle.x, particle.y);
              ctx.lineTo(other.x, other.y);
              ctx.stroke();
            }
          }
        }
      }
    }

    // Draw central energy field
    const avgIntensity = frequencyData.slice(0, usableDataLength).reduce((a, b) => a + b, 0) / usableDataLength / 255;
    if (avgIntensity > 0.3) {
      const fieldGradient = ctx.createRadialGradient(
        width / 2, height / 2, 0,
        width / 2, height / 2, 200 * avgIntensity
      );
      fieldGradient.addColorStop(0, primaryColor + '40');
      fieldGradient.addColorStop(0.5, primaryColor + '20');
      fieldGradient.addColorStop(1, 'transparent');

      ctx.fillStyle = fieldGradient;
      ctx.beginPath();
      ctx.arc(width / 2, height / 2, 200 * avgIntensity, 0, Math.PI * 2);
      ctx.fill();
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
