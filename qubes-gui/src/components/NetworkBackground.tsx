import React, { useEffect, useRef } from 'react';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
  isPurple?: boolean;
}

export const NetworkBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const animationFrameRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    const resizeCanvas = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Animation loop
    let time = 0;
    const animate = () => {
      time += 0.008;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Subtle grid with slight pulse
      const gridSize = 80;
      ctx.lineWidth = 1;

      // Vertical lines
      for (let x = 0; x < canvas.width; x += gridSize) {
        const pulse = Math.sin(time * 0.5 + x * 0.01) * 0.03 + 0.06;
        ctx.strokeStyle = `rgba(0, 255, 255, ${pulse})`;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();
      }

      // Horizontal lines
      for (let y = 0; y < canvas.height; y += gridSize) {
        const pulse = Math.sin(time * 0.5 + y * 0.01) * 0.03 + 0.06;
        ctx.strokeStyle = `rgba(0, 255, 255, ${pulse})`;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
      }

      // Glowing grid intersection points with wave (cyan and occasional purple)
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;

      for (let x = 0; x < canvas.width; x += gridSize) {
        for (let y = 0; y < canvas.height; y += gridSize) {
          const distToCenter = Math.sqrt(
            Math.pow(x - centerX, 2) + Math.pow(y - centerY, 2)
          );
          const pulse = Math.sin(time * 2 - distToCenter * 0.005) * 0.5 + 0.5;

          if (pulse > 0.7) {
            // Randomly choose purple or cyan (more purple)
            const isPurple = Math.sin(x * 0.01 + y * 0.01 + time) > 0.3; // More purple dots
            const color = isPurple ? '216, 34, 201' : '0, 255, 255';

            ctx.shadowBlur = 10;
            ctx.shadowColor = `rgba(${color}, ${pulse * 0.5})`;
            ctx.fillStyle = `rgba(${color}, ${pulse * 0.25})`;
            ctx.beginPath();
            ctx.arc(x, y, 2.5, 0, Math.PI * 2);
            ctx.fill();
            ctx.shadowBlur = 0;
          }
        }
      }

      // Spawn occasional glowing particles (cyan and purple mix - more frequent and visible)
      if (Math.random() > 0.94) {
        const isPurple = Math.random() > 0.5; // 50/50 purple and cyan
        particlesRef.current.push({
          x: Math.random() * canvas.width,
          y: Math.random() * canvas.height,
          vx: (Math.random() - 0.5) * 0.5,
          vy: (Math.random() - 0.5) * 0.5,
          life: 0,
          maxLife: Math.random() * 120 + 60,
          isPurple: isPurple,
        });
      }

      // Update and draw particles
      particlesRef.current = particlesRef.current.filter((particle) => {
        particle.life += 1;
        if (particle.life >= particle.maxLife) return false;

        particle.x += particle.vx;
        particle.y += particle.vy;

        const progress = particle.life / particle.maxLife;
        const alpha = Math.sin(progress * Math.PI) * 0.3; // Brighter particles

        // Subtle glow - cyan or purple
        const color = particle.isPurple ? '216, 34, 201' : '0, 255, 255'; // Purple (#d822c9) or cyan
        ctx.shadowBlur = 15;
        ctx.shadowColor = `rgba(${color}, ${alpha})`;
        ctx.fillStyle = `rgba(${color}, ${alpha})`;
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, 2, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;

        return true;
      });

      // Subtle radial gradient for depth
      const gradient = ctx.createRadialGradient(
        centerX,
        centerY,
        0,
        centerX,
        centerY,
        Math.max(canvas.width, canvas.height) * 0.6
      );
      gradient.addColorStop(0, 'rgba(20, 40, 60, 0.05)');
      gradient.addColorStop(1, 'rgba(10, 20, 30, 0)');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 0,
      }}
    />
  );
};
