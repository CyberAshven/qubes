import React, { useRef, useEffect } from 'react';

interface WaterRipplesProps {
  frequencyData: Uint8Array;
  colors: string | string[];
  width: number;
  height: number;
  frequencyRange: number;
}

interface Ripple {
  x: number;
  y: number;
  radius: number;
  maxRadius: number;
  life: number;
  hue: number;
  intensity: number;
}

export const WaterRipples: React.FC<WaterRipplesProps> = ({
  frequencyData,
  colors,
  width,
  height,
  frequencyRange
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const ripplesRef = useRef<Ripple[]>([]);
  const animationRef = useRef<number>(0);
  const prevIntensityRef = useRef<number>(0);
  const lastRippleRef = useRef<number>(0);

  // Get hue from colors
  const getHue = (): number => {
    const color = Array.isArray(colors) ? colors[0] : colors;
    const hex = color.replace('#', '');
    const r = parseInt(hex.substr(0, 2), 16);
    const g = parseInt(hex.substr(2, 2), 16);
    const b = parseInt(hex.substr(4, 2), 16);
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    let h = 0;
    if (max !== min) {
      const d = max - min;
      switch (max) {
        case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
        case g: h = ((b - r) / d + 2) / 6; break;
        case b: h = ((r - g) / d + 4) / 6; break;
      }
    }
    return h * 360;
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const baseHue = getHue();
    const centerX = width / 2;
    const centerY = height / 2;
    const maxRippleRadius = Math.max(width, height) * 0.8;

    const createRipple = (intensity: number, x?: number, y?: number) => {
      ripplesRef.current.push({
        x: x ?? centerX + (Math.random() - 0.5) * width * 0.3,
        y: y ?? centerY + (Math.random() - 0.5) * height * 0.3,
        radius: 0,
        maxRadius: maxRippleRadius * (0.5 + intensity * 0.5),
        life: 1,
        hue: baseHue + (Math.random() - 0.5) * 60,
        intensity
      });
    };

    const animate = () => {
      // Calculate audio intensity
      const dataLength = Math.floor(frequencyData.length * (frequencyRange / 100));
      let sum = 0;
      let bassSum = 0;
      for (let i = 0; i < dataLength; i++) {
        sum += frequencyData[i];
        if (i < dataLength * 0.2) {
          bassSum += frequencyData[i];
        }
      }
      const avgIntensity = dataLength > 0 ? sum / dataLength / 255 : 0;
      const bassIntensity = dataLength > 0 ? bassSum / (dataLength * 0.2) / 255 : 0;

      // Detect beats
      const intensityDelta = bassIntensity - prevIntensityRef.current;
      prevIntensityRef.current = bassIntensity * 0.8 + prevIntensityRef.current * 0.2;

      const now = Date.now();

      // Create ripples on beats
      if (intensityDelta > 0.1 && now - lastRippleRef.current > 100) {
        createRipple(bassIntensity, centerX, centerY);
        lastRippleRef.current = now;
      }

      // Ambient ripples
      if (avgIntensity > 0.2 && now - lastRippleRef.current > 300) {
        createRipple(avgIntensity * 0.7);
        lastRippleRef.current = now;
      }

      // Clear canvas with dark blue tint for water effect
      ctx.fillStyle = 'rgba(0, 5, 15, 0.15)';
      ctx.fillRect(0, 0, width, height);

      // Draw water surface gradient
      const surfaceGradient = ctx.createRadialGradient(
        centerX, centerY, 0,
        centerX, centerY, maxRippleRadius
      );
      surfaceGradient.addColorStop(0, `hsla(${baseHue}, 60%, 8%, 0.3)`);
      surfaceGradient.addColorStop(1, 'transparent');
      ctx.fillStyle = surfaceGradient;
      ctx.fillRect(0, 0, width, height);

      // Update and draw ripples
      const ripples = ripplesRef.current;
      for (let i = ripples.length - 1; i >= 0; i--) {
        const ripple = ripples[i];

        // Expand ripple
        const speed = 3 + ripple.intensity * 5;
        ripple.radius += speed;
        ripple.life = 1 - (ripple.radius / ripple.maxRadius);

        if (ripple.life <= 0) {
          ripples.splice(i, 1);
          continue;
        }

        // Draw multiple concentric rings per ripple
        const ringCount = 3;
        for (let r = 0; r < ringCount; r++) {
          const ringRadius = ripple.radius - r * 20;
          if (ringRadius < 0) continue;

          const alpha = ripple.life * (1 - r * 0.3) * ripple.intensity;
          const lightness = 50 + r * 15;

          // Outer glow
          ctx.beginPath();
          ctx.arc(ripple.x, ripple.y, ringRadius, 0, Math.PI * 2);
          ctx.strokeStyle = `hsla(${ripple.hue}, 80%, ${lightness}%, ${alpha * 0.3})`;
          ctx.lineWidth = 8 - r * 2;
          ctx.stroke();

          // Main ring
          ctx.beginPath();
          ctx.arc(ripple.x, ripple.y, ringRadius, 0, Math.PI * 2);
          ctx.strokeStyle = `hsla(${ripple.hue}, 90%, ${lightness + 20}%, ${alpha * 0.8})`;
          ctx.lineWidth = 3 - r;
          ctx.stroke();

          // Inner bright line
          ctx.beginPath();
          ctx.arc(ripple.x, ripple.y, ringRadius, 0, Math.PI * 2);
          ctx.strokeStyle = `hsla(${ripple.hue}, 100%, 80%, ${alpha})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }

        // Add shimmer/sparkle effect at ripple edge
        if (ripple.life > 0.3) {
          const sparkleCount = Math.floor(8 * ripple.intensity);
          for (let s = 0; s < sparkleCount; s++) {
            const angle = (Math.PI * 2 * s) / sparkleCount + ripple.radius * 0.01;
            const sparkleX = ripple.x + Math.cos(angle) * ripple.radius;
            const sparkleY = ripple.y + Math.sin(angle) * ripple.radius;
            const sparkleSize = 2 + Math.random() * 3 * ripple.intensity;

            const sparkleGradient = ctx.createRadialGradient(
              sparkleX, sparkleY, 0,
              sparkleX, sparkleY, sparkleSize * 2
            );
            sparkleGradient.addColorStop(0, `hsla(${ripple.hue}, 100%, 90%, ${ripple.life * 0.8})`);
            sparkleGradient.addColorStop(1, 'transparent');

            ctx.beginPath();
            ctx.arc(sparkleX, sparkleY, sparkleSize * 2, 0, Math.PI * 2);
            ctx.fillStyle = sparkleGradient;
            ctx.fill();
          }
        }
      }

      // Central glow that pulses with bass
      const centralGlow = ctx.createRadialGradient(
        centerX, centerY, 0,
        centerX, centerY, 100 + bassIntensity * 150
      );
      centralGlow.addColorStop(0, `hsla(${baseHue}, 100%, 70%, ${0.2 + bassIntensity * 0.4})`);
      centralGlow.addColorStop(0.5, `hsla(${baseHue}, 80%, 50%, ${0.1 + bassIntensity * 0.2})`);
      centralGlow.addColorStop(1, 'transparent');
      ctx.fillStyle = centralGlow;
      ctx.fillRect(0, 0, width, height);

      // Limit ripple count
      if (ripples.length > 20) {
        ripples.splice(0, ripples.length - 20);
      }

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
