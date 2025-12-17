import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Skill, SkillCategory } from '../../types';

interface MoonNodeProps {
  data: {
    skill: Skill;
    category?: SkillCategory;
    orbitRadius?: number;
    orbitAngle?: number;
    orbitCenter?: { x: number; y: number };
  };
}

export const MoonNode = memo(({ data }: MoonNodeProps) => {
  const { skill, category } = data;
  const color = category?.color || '#888';

  const progressPercent = (skill.xp / skill.maxXP) * 100;
  const isMaxed = skill.level === 100;

  return (
    <div className="relative w-[30px] h-[30px] group">
      {/* Main moon node with enhanced detail */}
      <div
        className="absolute inset-0 w-full h-full rounded-full flex items-center justify-center cursor-pointer transition-all hover:scale-150 hover:z-10 overflow-hidden"
        style={{
          background: skill.unlocked
            ? `radial-gradient(circle at 35% 25%, ${color}EE, ${color}BB 50%, ${color}88 80%, ${color}55)`
            : 'radial-gradient(circle at 35% 25%, #444, #2a2a2a 50%, #1a1a1a 80%, #0a0a0a)',
          boxShadow: skill.unlocked
            ? `0 0 8px ${color}60, inset -3px -3px 8px rgba(0,0,0,0.6), inset 2px 2px 5px rgba(255,255,255,0.3)`
            : '0 0 5px rgba(0,0,0,0.5), inset -2px -2px 5px rgba(0,0,0,0.8), inset 2px 2px 3px rgba(255,255,255,0.1)',
          border: skill.unlocked ? '1px solid rgba(255, 255, 255, 0.3)' : '1px solid rgba(255, 255, 255, 0.1)',
        }}
      >
        {/* Crater texture */}
        <div
          className="absolute inset-0 rounded-full"
          style={{
            background: `radial-gradient(circle at 60% 70%, rgba(0,0,0,0.3) 2px, transparent 3px),
                        radial-gradient(circle at 30% 40%, rgba(0,0,0,0.2) 1.5px, transparent 2px),
                        radial-gradient(circle at 70% 30%, rgba(0,0,0,0.25) 1px, transparent 1.5px)`,
            opacity: 0.4,
          }}
        />

        {/* Light reflection */}
        {skill.unlocked && (
          <div
            className="absolute inset-0 rounded-full"
            style={{
              background: `radial-gradient(circle at 30% 20%, rgba(255,255,255,0.5), transparent 40%)`,
            }}
          />
        )}
        {/* Icon or Lock */}
        {skill.unlocked && skill.icon ? (
          <div className="text-sm relative z-10">{skill.icon}</div>
        ) : !skill.unlocked ? (
          <div className="text-xs relative z-10">🔒</div>
        ) : null}

        {/* Maxed indicator */}
        {isMaxed && (
          <div className="absolute -top-0.5 -right-0.5 w-3 h-3 rounded-full bg-accent-primary flex items-center justify-center">
            <span className="text-[8px]">✨</span>
          </div>
        )}
      </div>

      {/* Always visible abbreviated name below moon */}
      <div className="absolute top-full mt-0.5 left-1/2 transform -translate-x-1/2 whitespace-nowrap">
        <div
          className="px-1 py-0.5 rounded text-[7px] font-semibold backdrop-blur-sm"
          style={{
            backgroundColor: `${color}25`,
            color: '#fff',
            border: `0.5px solid ${color}40`,
          }}
        >
          {skill.name.length > 12 ? skill.name.substring(0, 12) + '...' : skill.name}
        </div>
      </div>

      {/* Enhanced hover tooltip */}
      <div className="absolute bottom-full mb-1.5 left-1/2 transform -translate-x-1/2 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
        <div
          className="px-2 py-1.5 rounded-lg text-[9px] backdrop-blur-md"
          style={{
            backgroundColor: `${color}50`,
            color: '#fff',
            border: `1px solid ${color}90`,
            boxShadow: `0 3px 10px ${color}50`,
          }}
        >
          <div className="font-bold mb-0.5">{skill.name}</div>
          {skill.unlocked && (
            <>
              <div className="text-[8px] opacity-90">
                Level {skill.level} • {skill.xp}/{skill.maxXP} XP
              </div>
              <div className="text-[7px] opacity-80 mt-0.5">
                {Math.round(progressPercent)}% complete
              </div>
            </>
          )}
          {!skill.unlocked && (
            <div className="text-[8px] opacity-80">
              Locked - complete prerequisite
            </div>
          )}
        </div>
      </div>

      {/* XP Progress ring */}
      {skill.unlocked && (
        <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ transform: 'rotate(-90deg)' }}>
          <circle
            cx="15"
            cy="15"
            r="13"
            fill="none"
            stroke="rgba(255,255,255,0.1)"
            strokeWidth="1.5"
          />
          <circle
            cx="15"
            cy="15"
            r="13"
            fill="none"
            stroke="#00ff88"
            strokeWidth="1.5"
            strokeDasharray={`${2 * Math.PI * 13}`}
            strokeDashoffset={`${2 * Math.PI * 13 * (1 - progressPercent / 100)}`}
            style={{ transition: 'stroke-dashoffset 0.5s ease' }}
          />
        </svg>
      )}

      {/* Center connection handle */}
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
    </div>
  );
});

MoonNode.displayName = 'MoonNode';
