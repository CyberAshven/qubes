import { memo, useEffect, useRef } from 'react';
import { Handle, Position } from '@xyflow/react';
import * as d3 from 'd3';
import { Skill, SkillCategory } from '../../types';

// Format XP value for display (handles floating point precision)
const formatXP = (xp: number): string => {
  const rounded = Math.round(xp * 10) / 10;
  return Number.isInteger(rounded) ? rounded.toString() : rounded.toFixed(1);
};

interface SunNodeProps {
  data: {
    skill: Skill;
    category?: SkillCategory;
    orbitRadius?: number;
    orbitAngle?: number;
  };
}

export const SunNode = memo(({ data }: SunNodeProps) => {
  const { skill, category } = data;
  const svgRef = useRef<SVGSVGElement>(null);
  const color = category?.color || '#FFD700';

  // D3.js animation for glow effect
  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    const circle = svg.select('.sun-glow');

    // Pulsing glow animation
    const pulse = () => {
      circle
        .transition()
        .duration(2000)
        .attr('r', 105)
        .style('opacity', 0.6)
        .transition()
        .duration(2000)
        .attr('r', 95)
        .style('opacity', 0.3)
        .on('end', pulse);
    };

    pulse();

    return () => {
      circle.interrupt();
    };
  }, []);

  const progressPercent = (skill.xp / skill.maxXP) * 100;
  const isMaxed = skill.level === 100;

  return (
    <div className="relative w-[200px] h-[200px] group">
      {/* D3.js SVG for glow effects */}
      <svg
        ref={svgRef}
        className="absolute inset-0 w-full h-full"
        style={{ filter: 'blur(8px)', pointerEvents: 'none' }}
      >
        <defs>
          <radialGradient id={`sun-gradient-${skill.id}`}>
            <stop offset="0%" stopColor={color} stopOpacity="0.8" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle
          className="sun-glow"
          cx="100"
          cy="100"
          r="95"
          fill={`url(#sun-gradient-${skill.id})`}
          opacity="0.3"
        />
      </svg>

      {/* Main sun node with 3D sphere effect */}
      <div
        className="absolute inset-0 w-full h-full rounded-full flex flex-col items-center justify-center cursor-pointer transition-transform hover:scale-110 overflow-hidden"
        style={{
          background: `radial-gradient(circle at 35% 35%, ${color}FF, ${color}EE 30%, ${color}CC 60%, ${color}99 85%, ${color}66)`,
          boxShadow: `
            0 0 30px ${color}DD,
            0 0 60px ${color}80,
            inset -10px -10px 25px rgba(0,0,0,0.4),
            inset 10px 10px 20px rgba(255,255,255,0.4)
          `,
          border: '4px solid rgba(255, 255, 255, 0.5)',
        }}
      >
        {/* Solar flare effect */}
        <div
          className="absolute inset-0 rounded-full"
          style={{
            background: `
              radial-gradient(ellipse at 30% 30%, rgba(255,255,255,0.6), transparent 30%),
              radial-gradient(ellipse at 70% 60%, rgba(255,255,255,0.2), transparent 25%),
              radial-gradient(circle at 20% 80%, ${color}80, transparent 20%)
            `,
          }}
        />

        {/* Corona effect */}
        <div
          className="absolute inset-0 rounded-full"
          style={{
            background: `repeating-radial-gradient(circle, transparent, transparent 15px, rgba(255,255,255,0.05) 15px, rgba(255,255,255,0.05) 16px)`,
          }}
        />
        {/* Icon */}
        <div className="text-5xl mb-1">{category?.icon || '☀️'}</div>

        {/* Name */}
        <div className="text-sm font-bold text-white text-center px-2 leading-tight mb-1">
          {skill.name}
        </div>

        {/* Level */}
        <div className="text-xs font-semibold text-white/90">Level {skill.level}</div>

        {/* XP Bar integrated */}
        <div className="w-[140px] bg-black/30 rounded-full h-1.5 mt-2 border border-white/20">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${progressPercent}%`,
              background: `linear-gradient(90deg, ${color}, #00ff88)`,
              boxShadow: `0 0 6px ${color}80`,
            }}
          />
        </div>
        <div className="text-[9px] text-white/70 mt-0.5">
          {formatXP(skill.xp)}/{skill.maxXP} XP
        </div>

        {/* Unlock indicator */}
        {!skill.unlocked && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/60 rounded-full backdrop-blur-sm">
            <div className="text-4xl">🔒</div>
          </div>
        )}

        {/* Maxed indicator */}
        {isMaxed && (
          <div className="absolute -top-2 -right-2 w-8 h-8 rounded-full bg-accent-primary flex items-center justify-center">
            <span className="text-sm">✨</span>
          </div>
        )}
      </div>

      {/* Enhanced hover tooltip with category details */}
      <div className="absolute bottom-full mb-4 left-1/2 transform -translate-x-1/2 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
        <div
          className="px-4 py-3 rounded-lg text-sm backdrop-blur-md"
          style={{
            backgroundColor: `${color}50`,
            color: '#fff',
            border: `2px solid ${color}90`,
            boxShadow: `0 6px 20px ${color}70`,
          }}
        >
          <div className="font-bold mb-1 text-base">{category?.icon} {skill.name}</div>
          <div className="text-xs opacity-90 mb-1">
            Level {skill.level} • {formatXP(skill.xp)}/{skill.maxXP} XP ({Math.round(progressPercent)}%)
          </div>
          <div className="text-xs opacity-80 mb-2">
            Tier: {skill.tier}
          </div>
          <div className="text-xs opacity-90 border-t border-white/20 pt-2">
            {skill.description}
          </div>
        </div>
      </div>

      {/* Center connection handles */}
      <Handle
        type="target"
        position={Position.Top}
        style={{
          opacity: 0,
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
        }}
      />
      <Handle
        type="source"
        position={Position.Top}
        style={{
          opacity: 0,
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
        }}
      />
    </div>
  );
});

SunNode.displayName = 'SunNode';
