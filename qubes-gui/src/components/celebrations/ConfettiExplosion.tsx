import React, { useEffect, useRef } from 'react';
import { useCelebration } from '../../contexts/CelebrationContext';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  color: string;
  rotation: number;
  rotationSpeed: number;
  scale: number;
  type: 'confetti' | 'star' | 'circle';
  life: number;
}

interface ConfettiExplosionProps {
  color?: string;
  particleCount?: number;
  duration?: number;
}

// Helper to adjust color brightness
function adjustColor(color: string, amount: number): string {
  const hex = color.replace('#', '');
  const r = Math.max(0, Math.min(255, parseInt(hex.substring(0, 2), 16) + amount));
  const g = Math.max(0, Math.min(255, parseInt(hex.substring(2, 4), 16) + amount));
  const b = Math.max(0, Math.min(255, parseInt(hex.substring(4, 6), 16) + amount));
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

// Helper to draw a star
function drawStar(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  spikes: number,
  outerRadius: number,
  innerRadius: number
) {
  let rot = (Math.PI / 2) * 3;
  let x = cx;
  let y = cy;
  const step = Math.PI / spikes;

  ctx.beginPath();
  ctx.moveTo(cx, cy - outerRadius);

  for (let i = 0; i < spikes; i++) {
    x = cx + Math.cos(rot) * outerRadius;
    y = cy + Math.sin(rot) * outerRadius;
    ctx.lineTo(x, y);
    rot += step;

    x = cx + Math.cos(rot) * innerRadius;
    y = cy + Math.sin(rot) * innerRadius;
    ctx.lineTo(x, y);
    rot += step;
  }

  ctx.lineTo(cx, cy - outerRadius);
  ctx.closePath();
  ctx.fill();
}

export const ConfettiExplosion: React.FC<ConfettiExplosionProps> = ({
  color = '#00ff88',
  particleCount = 100,
  duration = 3000,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { settings } = useCelebration();

  useEffect(() => {
    if (settings.reducedMotion || !settings.confetti) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    // Generate color palette based on main color
    const colors = [
      color,
      adjustColor(color, 30),
      adjustColor(color, -30),
      '#FFD700', // Gold
      '#FFFFFF', // White
    ];

    // Create particles
    const particles: Particle[] = [];
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;

    for (let i = 0; i < particleCount; i++) {
      const angle = (Math.PI * 2 * i) / particleCount + Math.random() * 0.5;
      const velocity = 5 + Math.random() * 10;

      particles.push({
        x: centerX,
        y: centerY,
        vx: Math.cos(angle) * velocity,
        vy: Math.sin(angle) * velocity - 5, // Initial upward bias
        color: colors[Math.floor(Math.random() * colors.length)],
        rotation: Math.random() * Math.PI * 2,
        rotationSpeed: (Math.random() - 0.5) * 0.2,
        scale: 0.5 + Math.random() * 0.5,
        type: ['confetti', 'star', 'circle'][Math.floor(Math.random() * 3)] as Particle['type'],
        life: 1,
      });
    }

    const startTime = Date.now();
    let animationId: number;

    const animate = () => {
      const elapsed = Date.now() - startTime;
      if (elapsed > duration) {
        return;
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      particles.forEach(particle => {
        // Update physics
        particle.vy += 0.15; // Gravity
        particle.x += particle.vx;
        particle.y += particle.vy;
        particle.rotation += particle.rotationSpeed;
        particle.vx *= 0.99; // Air resistance
        particle.life = Math.max(0, 1 - elapsed / duration);

        // Draw particle
        ctx.save();
        ctx.translate(particle.x, particle.y);
        ctx.rotate(particle.rotation);
        ctx.globalAlpha = particle.life;
        ctx.fillStyle = particle.color;

        const size = 10 * particle.scale;

        switch (particle.type) {
          case 'confetti':
            ctx.fillRect(-size / 2, -size / 4, size, size / 2);
            break;
          case 'star':
            drawStar(ctx, 0, 0, 5, size / 2, size / 4);
            break;
          case 'circle':
            ctx.beginPath();
            ctx.arc(0, 0, size / 3, 0, Math.PI * 2);
            ctx.fill();
            break;
        }

        ctx.restore();
      });

      animationId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
    };
  }, [color, particleCount, duration, settings.reducedMotion, settings.confetti]);

  if (settings.reducedMotion || !settings.confetti) {
    return null;
  }

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-[100]"
      style={{ mixBlendMode: 'screen' }}
    />
  );
};

export default ConfettiExplosion;
