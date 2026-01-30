import React, { useEffect, useRef, useState } from 'react';

interface AvatarFaceProps {
  frequencyData: Uint8Array;
  colors: string | string[];
  width: number;
  height: number;
  frequencyRange: number;
  avatarUrl?: string;
  intensity?: number; // 1-6, default 1
}

/**
 * Avatar Face - Displays the Qube's avatar with audio-reactive effects
 * Intensity levels 1-6 add progressively more elaborate effects
 */
export const AvatarFace: React.FC<AvatarFaceProps> = ({
  frequencyData,
  colors,
  width,
  height,
  frequencyRange,
  avatarUrl,
  intensity = 1
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const phaseRef = useRef<number>(0);
  const particlesRef = useRef<Array<{
    x: number, y: number, vx: number, vy: number,
    life: number, maxLife: number, size: number,
    hue?: number, type?: string
  }>>([]);
  const trailsRef = useRef<Array<{x: number, y: number, alpha: number}>>([]);
  const lightningRef = useRef<Array<{points: Array<{x: number, y: number}>, life: number}>>([]);

  // Load the avatar image
  useEffect(() => {
    if (!avatarUrl) {
      setImageError(true);
      return;
    }

    const img = new Image();
    img.crossOrigin = 'anonymous';

    img.onload = () => {
      imageRef.current = img;
      setImageLoaded(true);
      setImageError(false);
    };

    img.onerror = () => {
      setImageError(true);
      setImageLoaded(false);
    };

    img.src = avatarUrl;

    return () => {
      img.onload = null;
      img.onerror = null;
    };
  }, [avatarUrl]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = width;
    canvas.height = height;
    ctx.clearRect(0, 0, width, height);

    const primaryColor = Array.isArray(colors) ? colors[0] : colors;
    const secondaryColor = Array.isArray(colors) ? (colors[1] || colors[0]) : colors;

    // Parse colors
    const r = parseInt(primaryColor.slice(1, 3), 16);
    const g = parseInt(primaryColor.slice(3, 5), 16);
    const b = parseInt(primaryColor.slice(5, 7), 16);

    // Audio analysis
    const usableLength = Math.floor(frequencyData.length * (frequencyRange / 100));
    let lowFreqSum = 0, midFreqSum = 0, highFreqSum = 0, totalSum = 0;
    const lowEnd = Math.floor(usableLength * 0.3);
    const midEnd = Math.floor(usableLength * 0.6);

    for (let i = 0; i < usableLength; i++) {
      const val = frequencyData[i];
      totalSum += val;
      if (i < lowEnd) lowFreqSum += val;
      else if (i < midEnd) midFreqSum += val;
      else highFreqSum += val;
    }

    const lowFreqAvg = lowFreqSum / lowEnd / 255;
    const midFreqAvg = midFreqSum / (midEnd - lowEnd) / 255;
    const highFreqAvg = highFreqSum / (usableLength - midEnd) / 255;
    const overallAvg = totalSum / usableLength / 255;

    const centerX = width / 2;
    const centerY = height / 2;
    const baseSize = Math.min(width, height) * 0.45;

    // Update phase (faster at higher intensities)
    phaseRef.current += 0.03 + intensity * 0.015;

    // Helper: get color with optional rainbow mode (intensity >= 4)
    const getColor = (alpha: number, hueOffset: number = 0): string => {
      if (intensity >= 4) {
        const hue = (phaseRef.current * 20 + hueOffset) % 360;
        return `hsla(${hue}, 80%, 60%, ${alpha})`;
      }
      return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    };

    // === LEVEL 6: COSMIC BACKGROUND (stars, nebula) ===
    if (intensity >= 6) {
      // Nebula clouds
      for (let i = 0; i < 3; i++) {
        const nebulaX = centerX + Math.cos(phaseRef.current * 0.1 + i * 2) * width * 0.3;
        const nebulaY = centerY + Math.sin(phaseRef.current * 0.15 + i * 2) * height * 0.3;
        const nebulaSize = baseSize * (0.8 + overallAvg * 0.5);
        const nebulaGrad = ctx.createRadialGradient(nebulaX, nebulaY, 0, nebulaX, nebulaY, nebulaSize);
        const hue = (phaseRef.current * 10 + i * 120) % 360;
        nebulaGrad.addColorStop(0, `hsla(${hue}, 70%, 50%, ${0.15 * overallAvg})`);
        nebulaGrad.addColorStop(0.5, `hsla(${hue + 30}, 60%, 40%, ${0.08 * overallAvg})`);
        nebulaGrad.addColorStop(1, 'transparent');
        ctx.fillStyle = nebulaGrad;
        ctx.fillRect(0, 0, width, height);
      }

      // Stars
      const starCount = 50 + Math.floor(overallAvg * 50);
      for (let i = 0; i < starCount; i++) {
        const starX = (Math.sin(i * 123.456 + phaseRef.current * 0.1) * 0.5 + 0.5) * width;
        const starY = (Math.cos(i * 789.012 + phaseRef.current * 0.08) * 0.5 + 0.5) * height;
        const twinkle = Math.sin(phaseRef.current * 3 + i) * 0.5 + 0.5;
        const starSize = 1 + twinkle * 2 * (overallAvg + 0.3);

        ctx.beginPath();
        ctx.arc(starX, starY, starSize, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${0.3 + twinkle * 0.5})`;
        ctx.fill();
      }
    }

    // === LEVEL 5+: LIGHTNING ===
    if (intensity >= 5 && overallAvg > 0.5 && Math.random() < overallAvg * 0.3) {
      const angle = Math.random() * Math.PI * 2;
      const startDist = baseSize * 0.6;
      const points: Array<{x: number, y: number}> = [];
      let x = centerX + Math.cos(angle) * startDist;
      let y = centerY + Math.sin(angle) * startDist;
      points.push({x, y});

      const segments = 5 + Math.floor(Math.random() * 5);
      for (let i = 0; i < segments; i++) {
        x += (Math.random() - 0.5) * 80;
        y += (Math.random() - 0.5) * 80;
        points.push({x, y});
      }
      lightningRef.current.push({ points, life: 10 });
    }

    // Draw and update lightning
    lightningRef.current = lightningRef.current.filter(bolt => {
      bolt.life -= 1;
      if (bolt.life > 0) {
        ctx.beginPath();
        ctx.moveTo(bolt.points[0].x, bolt.points[0].y);
        for (let i = 1; i < bolt.points.length; i++) {
          ctx.lineTo(bolt.points[i].x, bolt.points[i].y);
        }
        const alpha = bolt.life / 10;
        ctx.strokeStyle = intensity >= 6
          ? `hsla(${(phaseRef.current * 50) % 360}, 100%, 70%, ${alpha})`
          : `rgba(255, 255, 255, ${alpha})`;
        ctx.lineWidth = 2 + bolt.life * 0.3;
        ctx.stroke();

        // Glow
        ctx.strokeStyle = getColor(alpha * 0.5);
        ctx.lineWidth = 8;
        ctx.stroke();
        return true;
      }
      return false;
    });

    // === AMBIENT GLOW (scales with intensity) ===
    const glowLayers = Math.min(intensity, 4);
    for (let i = 0; i < glowLayers; i++) {
      const glowSize = baseSize * (1 + i * 0.3 + overallAvg * 0.3);
      const ambientGrad = ctx.createRadialGradient(centerX, centerY, baseSize * 0.2, centerX, centerY, glowSize);
      ambientGrad.addColorStop(0, getColor(0.15 / (i + 1) + overallAvg * 0.1));
      ambientGrad.addColorStop(0.5, getColor(0.08 / (i + 1) + overallAvg * 0.05));
      ambientGrad.addColorStop(1, 'transparent');
      ctx.fillStyle = ambientGrad;
      ctx.fillRect(0, 0, width, height);
    }

    // === RINGS (more rings at higher intensity) ===
    const numRings = intensity + 2;
    for (let i = 0; i < numRings; i++) {
      const ringPhase = phaseRef.current * (1 + intensity * 0.2) + i * 0.4;
      const ringPulse = Math.sin(ringPhase) * 0.5 + 0.5;
      const ringRadius = baseSize * 0.55 + baseSize * 0.12 * i + ringPulse * overallAvg * baseSize * 0.2;
      const ringAlpha = (0.2 - i * 0.02) * (0.5 + overallAvg);

      ctx.beginPath();
      ctx.arc(centerX, centerY, ringRadius, 0, Math.PI * 2);
      ctx.strokeStyle = getColor(ringAlpha, i * 30);
      ctx.lineWidth = 2 + overallAvg * (intensity * 0.5);
      ctx.stroke();
    }

    // === LEVEL 3+: WAVEFORM RING ===
    if (intensity >= 3 && overallAvg > 0.05) {
      const waveRadius = baseSize * 0.6;
      const segments = 64 + intensity * 16;

      ctx.beginPath();
      for (let i = 0; i <= segments; i++) {
        const angle = (i / segments) * Math.PI * 2 - Math.PI / 2;
        const freqIndex = Math.floor((i / segments) * Math.min(usableLength, 64));
        const freqValue = frequencyData[freqIndex] / 255;
        const waveOffset = freqValue * baseSize * (0.1 + intensity * 0.03);
        const px = centerX + Math.cos(angle) * (waveRadius + waveOffset);
        const py = centerY + Math.sin(angle) * (waveRadius + waveOffset);

        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
      ctx.strokeStyle = getColor(0.4 + overallAvg * 0.4, 60);
      ctx.lineWidth = 1.5 + intensity * 0.5;
      ctx.stroke();

      // Fill at higher intensities
      if (intensity >= 5) {
        ctx.fillStyle = getColor(0.1 + overallAvg * 0.1, 60);
        ctx.fill();
      }
    }

    // === LEVEL 4+: GEOMETRIC SHAPES ===
    if (intensity >= 4) {
      const shapeCount = intensity - 2;
      for (let s = 0; s < shapeCount; s++) {
        const shapeAngle = phaseRef.current * (0.5 + s * 0.2) + s * Math.PI / shapeCount;
        const shapeDist = baseSize * (0.7 + s * 0.15);
        const shapeSize = baseSize * 0.1 * (1 + overallAvg);
        const sides = 3 + s;

        ctx.beginPath();
        for (let i = 0; i <= sides; i++) {
          const a = shapeAngle + (i / sides) * Math.PI * 2;
          const px = centerX + Math.cos(shapeAngle) * shapeDist + Math.cos(a) * shapeSize;
          const py = centerY + Math.sin(shapeAngle) * shapeDist + Math.sin(a) * shapeSize;
          if (i === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.closePath();
        ctx.strokeStyle = getColor(0.3 + overallAvg * 0.3, s * 60);
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }

    // === PARTICLES (more at higher intensity) ===
    const particleSpawnRate = intensity * 0.15;
    const maxParticles = 30 + intensity * 20;

    if (overallAvg > 0.3 && Math.random() < overallAvg * particleSpawnRate) {
      const angle = Math.random() * Math.PI * 2;
      const speed = (1 + overallAvg * 2) * (1 + intensity * 0.3);
      particlesRef.current.push({
        x: centerX + Math.cos(angle) * baseSize * 0.5,
        y: centerY + Math.sin(angle) * baseSize * 0.5,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        life: 0,
        maxLife: 40 + Math.random() * 40 + intensity * 10,
        size: 2 + Math.random() * 3 + intensity,
        hue: Math.random() * 360,
        type: intensity >= 5 && Math.random() > 0.7 ? 'star' : 'circle'
      });
    }

    // Update and draw particles
    particlesRef.current = particlesRef.current.filter(p => {
      p.x += p.vx;
      p.y += p.vy;
      p.life += 1;
      p.vx *= 0.98;
      p.vy *= 0.98;

      // Add gravity at level 6
      if (intensity >= 6) {
        p.vy += 0.02;
      }

      if (p.life < p.maxLife) {
        const alpha = 1 - (p.life / p.maxLife);
        const size = p.size * (1 + (1 - alpha) * 0.5);

        // Trail at intensity 5+
        if (intensity >= 5) {
          trailsRef.current.push({ x: p.x, y: p.y, alpha: alpha * 0.3 });
        }

        ctx.beginPath();
        if (p.type === 'star') {
          // Draw star shape
          const spikes = 4;
          for (let i = 0; i < spikes * 2; i++) {
            const r = i % 2 === 0 ? size : size * 0.4;
            const a = (i / (spikes * 2)) * Math.PI * 2 + phaseRef.current;
            const sx = p.x + Math.cos(a) * r;
            const sy = p.y + Math.sin(a) * r;
            if (i === 0) ctx.moveTo(sx, sy);
            else ctx.lineTo(sx, sy);
          }
          ctx.closePath();
        } else {
          ctx.arc(p.x, p.y, size, 0, Math.PI * 2);
        }

        ctx.fillStyle = intensity >= 4
          ? `hsla(${p.hue}, 80%, 60%, ${alpha * 0.7})`
          : getColor(alpha * 0.6);
        ctx.fill();
        return true;
      }
      return false;
    });

    // Limit particles
    if (particlesRef.current.length > maxParticles) {
      particlesRef.current = particlesRef.current.slice(-maxParticles);
    }

    // Draw trails (level 5+)
    if (intensity >= 5) {
      trailsRef.current = trailsRef.current.filter(t => {
        t.alpha -= 0.02;
        if (t.alpha > 0) {
          ctx.beginPath();
          ctx.arc(t.x, t.y, 2, 0, Math.PI * 2);
          ctx.fillStyle = getColor(t.alpha, 90);
          ctx.fill();
          return true;
        }
        return false;
      });
      if (trailsRef.current.length > 200) {
        trailsRef.current = trailsRef.current.slice(-200);
      }
    }

    // === AVATAR ===
    if (imageLoaded && imageRef.current) {
      const img = imageRef.current;

      // Pulse intensity scales with level
      const breathe = Math.sin(phaseRef.current * 0.5) * (0.015 + intensity * 0.005);
      const audioPulse = lowFreqAvg * (0.05 + intensity * 0.02);
      const pulseScale = 1 + breathe + audioPulse;

      const maxSize = baseSize * 0.9;
      const scale = Math.min(maxSize / img.width, maxSize / img.height) * pulseScale;
      const imgWidth = img.width * scale;
      const imgHeight = img.height * scale;
      const imgX = centerX - imgWidth / 2;
      const imgY = centerY - imgHeight / 2;
      const avatarRadius = Math.min(imgWidth, imgHeight) / 2;

      // Glow behind avatar
      const glowIntensity = (0.3 + overallAvg * 0.5) * (1 + intensity * 0.15);
      const glowSize = avatarRadius * (1.3 + intensity * 0.1);
      const glowGrad = ctx.createRadialGradient(centerX, centerY, avatarRadius * 0.5, centerX, centerY, glowSize);
      glowGrad.addColorStop(0, getColor(glowIntensity * 0.6));
      glowGrad.addColorStop(0.6, getColor(glowIntensity * 0.3, 30));
      glowGrad.addColorStop(1, 'transparent');
      ctx.fillStyle = glowGrad;
      ctx.beginPath();
      ctx.arc(centerX, centerY, glowSize, 0, Math.PI * 2);
      ctx.fill();

      // Draw avatar
      ctx.save();
      ctx.beginPath();
      ctx.arc(centerX, centerY, avatarRadius, 0, Math.PI * 2);
      ctx.clip();
      ctx.drawImage(img, imgX, imgY, imgWidth, imgHeight);

      // Color overlay (more intense at higher levels)
      if (intensity >= 2) {
        ctx.fillStyle = getColor(overallAvg * (0.1 + intensity * 0.03));
        ctx.fillRect(imgX, imgY, imgWidth, imgHeight);
      }
      ctx.restore();

      // Border
      const borderWidth = 3 + overallAvg * (3 + intensity);
      ctx.beginPath();
      ctx.arc(centerX, centerY, avatarRadius, 0, Math.PI * 2);
      ctx.strokeStyle = getColor(0.8 + overallAvg * 0.2);
      ctx.lineWidth = borderWidth;
      ctx.stroke();

      // Inner glow ring
      if (intensity >= 2) {
        ctx.beginPath();
        ctx.arc(centerX, centerY, avatarRadius - borderWidth / 2, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(255, 255, 255, ${0.15 + overallAvg * 0.2})`;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

    } else if (imageError || !avatarUrl) {
      // Placeholder
      const placeholderRadius = baseSize * 0.35;
      ctx.beginPath();
      ctx.arc(centerX, centerY, placeholderRadius, 0, Math.PI * 2);
      ctx.fillStyle = getColor(0.2);
      ctx.fill();
      ctx.strokeStyle = getColor(0.8);
      ctx.lineWidth = 3;
      ctx.stroke();

      ctx.fillStyle = getColor(0.6);
      ctx.font = '14px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('No avatar', centerX, centerY + placeholderRadius + 25);
    } else {
      ctx.fillStyle = getColor(0.5);
      ctx.font = '16px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('Loading...', centerX, centerY);
    }

    // === LEVEL 3+: ORBITING ENERGY DOTS ===
    if (intensity >= 3 && highFreqAvg > 0.2) {
      const dotCount = 4 + intensity * 2;
      for (let i = 0; i < dotCount; i++) {
        const orbitSpeed = 0.3 + (i % 3) * 0.1;
        const angle = phaseRef.current * orbitSpeed + (i / dotCount) * Math.PI * 2;
        const dist = baseSize * (0.6 + (i % 2) * 0.15) + Math.sin(phaseRef.current * 2 + i) * baseSize * 0.05;
        const dx = centerX + Math.cos(angle) * dist;
        const dy = centerY + Math.sin(angle) * dist;
        const dotSize = 2 + highFreqAvg * (3 + intensity);

        ctx.beginPath();
        ctx.arc(dx, dy, dotSize, 0, Math.PI * 2);
        ctx.fillStyle = intensity >= 4
          ? `hsla(${(phaseRef.current * 30 + i * 30) % 360}, 80%, 70%, ${0.4 + highFreqAvg * 0.4})`
          : `rgba(255, 255, 255, ${0.3 + highFreqAvg * 0.4})`;
        ctx.fill();

        // Dot glow at higher levels
        if (intensity >= 4) {
          ctx.beginPath();
          ctx.arc(dx, dy, dotSize * 2, 0, Math.PI * 2);
          ctx.fillStyle = getColor(0.15, i * 30);
          ctx.fill();
        }
      }
    }

    // === LEVEL 6: OUTER SPIRAL ===
    if (intensity >= 6 && overallAvg > 0.3) {
      ctx.beginPath();
      for (let i = 0; i < 200; i++) {
        const t = i / 200;
        const spiralAngle = t * Math.PI * 6 + phaseRef.current;
        const spiralDist = baseSize * (0.8 + t * 0.7);
        const sx = centerX + Math.cos(spiralAngle) * spiralDist;
        const sy = centerY + Math.sin(spiralAngle) * spiralDist;
        if (i === 0) ctx.moveTo(sx, sy);
        else ctx.lineTo(sx, sy);
      }
      ctx.strokeStyle = getColor(0.2 + overallAvg * 0.2, 120);
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

  }, [frequencyData, colors, width, height, frequencyRange, imageLoaded, imageError, avatarUrl, intensity]);

  return (
    <canvas
      ref={canvasRef}
      style={{ width: `${width}px`, height: `${height}px`, display: 'block', position: 'absolute', top: 0, left: 0 }}
    />
  );
};
