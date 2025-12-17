import { memo, useEffect, useRef } from 'react';
import { Handle, Position } from '@xyflow/react';
import * as d3 from 'd3';
import { Skill, SkillCategory } from '../../types';

interface PlanetNodeProps {
  data: {
    skill: Skill;
    category?: SkillCategory;
    orbitRadius?: number;
    orbitAngle?: number;
    orbitCenter?: { x: number; y: number };
  };
}

export const PlanetNode = memo(({ data }: PlanetNodeProps) => {
  const { skill, category } = data;
  const svgRef = useRef<SVGSVGElement>(null);
  const color = category?.color || '#4A90E2';

  // D3.js subtle glow animation
  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    const circle = svg.select('.planet-glow');

    const pulse = () => {
      circle
        .transition()
        .duration(3000)
        .attr('r', 35)
        .style('opacity', 0.4)
        .transition()
        .duration(3000)
        .attr('r', 28)
        .style('opacity', 0.2)
        .on('end', pulse);
    };

    if (skill.unlocked) {
      pulse();
    }

    return () => {
      circle.interrupt();
    };
  }, [skill.unlocked]);

  const progressPercent = (skill.xp / skill.maxXP) * 100;
  const isMaxed = skill.level === 100;

  return (
    <div className="relative w-[60px] h-[60px] group">
      {/* D3.js SVG for glow */}
      {skill.unlocked && (
        <svg
          ref={svgRef}
          className="absolute inset-0 w-full h-full"
          style={{ filter: 'blur(6px)', pointerEvents: 'none' }}
        >
          <defs>
            <radialGradient id={`planet-gradient-${skill.id}`}>
              <stop offset="0%" stopColor={color} stopOpacity="0.6" />
              <stop offset="100%" stopColor={color} stopOpacity="0" />
            </radialGradient>
          </defs>
          <circle
            className="planet-glow"
            cx="30"
            cy="30"
            r="28"
            fill={`url(#planet-gradient-${skill.id})`}
            opacity="0.2"
          />
        </svg>
      )}

      {/* Main planet node with enhanced visuals */}
      <div
        className="absolute inset-0 w-full h-full rounded-full flex items-center justify-center cursor-pointer transition-all hover:scale-125 hover:z-10 overflow-hidden"
        style={{
          background: skill.unlocked
            ? `radial-gradient(circle at 30% 30%, ${color}FF, ${color}DD 40%, ${color}AA 70%, ${color}77)`
            : 'radial-gradient(circle at 30% 30%, #555, #333 40%, #222 70%, #111)',
          boxShadow: skill.unlocked
            ? `0 0 15px ${color}80, inset -5px -5px 15px rgba(0,0,0,0.5), inset 5px 5px 10px rgba(255,255,255,0.3)`
            : '0 0 10px rgba(0,0,0,0.5), inset -3px -3px 8px rgba(0,0,0,0.8), inset 3px 3px 8px rgba(255,255,255,0.1)',
          border: skill.unlocked ? '2px solid rgba(255, 255, 255, 0.4)' : '2px solid rgba(255, 255, 255, 0.1)',
        }}
      >
        {/* Surface texture overlay */}
        <div
          className="absolute inset-0 rounded-full"
          style={{
            background: `repeating-linear-gradient(45deg, transparent, transparent 5px, rgba(0,0,0,0.1) 5px, rgba(0,0,0,0.1) 6px)`,
            opacity: 0.3,
          }}
        />

        {/* Atmospheric glow */}
        {skill.unlocked && (
          <div
            className="absolute inset-0 rounded-full"
            style={{
              background: `radial-gradient(circle at 25% 25%, rgba(255,255,255,0.4), transparent 50%)`,
            }}
          />
        )}
        {/* Icon and Level */}
        {skill.unlocked && (
          <div className="flex flex-col items-center relative z-10">
            {skill.icon && <div className="text-lg mb-0.5">{skill.icon}</div>}
            <div className="text-xs font-bold text-white">{skill.level}</div>
          </div>
        )}

        {/* Lock icon */}
        {!skill.unlocked && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-xl">🔒</div>
          </div>
        )}

        {/* Maxed indicator */}
        {isMaxed && (
          <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-accent-primary flex items-center justify-center">
            <span className="text-xs">✨</span>
          </div>
        )}
      </div>

      {/* Always visible skill name below */}
      <div className="absolute top-full mt-1 left-1/2 transform -translate-x-1/2 whitespace-nowrap">
        <div
          className="px-1.5 py-0.5 rounded text-[9px] font-semibold backdrop-blur-sm"
          style={{
            backgroundColor: `${color}30`,
            color: '#fff',
            border: `1px solid ${color}50`,
          }}
        >
          {skill.name}
        </div>
      </div>

      {/* Enhanced hover tooltip with full details */}
      <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
        <div
          className="px-3 py-2 rounded-lg text-[10px] backdrop-blur-md"
          style={{
            backgroundColor: `${color}50`,
            color: '#fff',
            border: `1px solid ${color}90`,
            boxShadow: `0 4px 12px ${color}60`,
          }}
        >
          <div className="font-bold mb-1">{skill.name}</div>
          {skill.unlocked && (
            <>
              <div className="text-[9px] opacity-90 mb-1">
                Level {skill.level} • {skill.xp}/{skill.maxXP} XP ({Math.round(progressPercent)}%)
              </div>
              <div className="text-[8px] opacity-80">
                Tier: {skill.tier}
              </div>
            </>
          )}
          {skill.toolCallReward && (
            <div className="text-[9px] text-accent-primary mt-1.5 border-t border-white/20 pt-1">
              🎁 Unlocks: {skill.toolCallReward}()
            </div>
          )}
        </div>
      </div>

      {/* XP Progress ring */}
      {skill.unlocked && (
        <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ transform: 'rotate(-90deg)' }}>
          <circle
            cx="30"
            cy="30"
            r="28"
            fill="none"
            stroke="rgba(255,255,255,0.15)"
            strokeWidth="2"
          />
          <circle
            cx="30"
            cy="30"
            r="28"
            fill="none"
            stroke="#00ff88"
            strokeWidth="2"
            strokeDasharray={`${2 * Math.PI * 28}`}
            strokeDashoffset={`${2 * Math.PI * 28 * (1 - progressPercent / 100)}`}
            style={{ transition: 'stroke-dashoffset 0.5s ease' }}
          />
        </svg>
      )}

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

PlanetNode.displayName = 'PlanetNode';
