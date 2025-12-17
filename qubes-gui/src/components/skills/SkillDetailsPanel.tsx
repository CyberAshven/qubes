import { memo, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Skill, SkillCategory } from '../../types';
import { GlassCard, GlassButton } from '../glass';
import { useAuth } from '../../hooks/useAuth';

interface SkillDetailsPanelProps {
  skill: Skill;
  category?: SkillCategory;
  allSkills: Skill[];
  qubeId: string;
  onClose: () => void;
  onSkillUnlocked?: () => void;
}

const TIER_LABELS: Record<string, string> = {
  novice: 'Novice',
  intermediate: 'Intermediate',
  advanced: 'Advanced',
  expert: 'Expert',
};

const TIER_COLORS: Record<string, string> = {
  novice: '#888888',
  intermediate: '#4A90E2',
  advanced: '#9B59B6',
  expert: '#F39C12',
};

export const SkillDetailsPanel = memo(({ skill, category, allSkills, qubeId, onClose, onSkillUnlocked }: SkillDetailsPanelProps) => {
  const { userId } = useAuth();
  const [isUnlocking, setIsUnlocking] = useState(false);
  const progressPercent = (skill.xp / skill.maxXP) * 100;
  const tierLabel = TIER_LABELS[skill.tier] || skill.tier;
  const tierColor = TIER_COLORS[skill.tier] || '#888';
  const color = category?.color || '#888';

  // Find parent skill to check if unlock is possible
  const parentSkill = skill.parentSkill
    ? allSkills.find((s) => s.id === skill.parentSkill)
    : null;

  // Determine unlock threshold based on node type
  const getUnlockThreshold = (nodeType: string): number => {
    if (nodeType === 'planet') return 100; // Planets unlock every 100 sun XP
    if (nodeType === 'moon') return 50;    // Moons unlock every 50 planet XP
    return 0;
  };

  const unlockThreshold = getUnlockThreshold(skill.nodeType);
  const canUnlock = !skill.unlocked && parentSkill && parentSkill.unlocked && parentSkill.xp >= unlockThreshold;

  const handleUnlock = async () => {
    if (!canUnlock || !userId) return;

    setIsUnlocking(true);
    try {
      await invoke('unlock_skill', {
        userId,
        qubeId,
        skillId: skill.id,
      });

      // Notify parent to reload skills
      if (onSkillUnlocked) {
        onSkillUnlocked();
      }
    } catch (error) {
      console.error('Failed to unlock skill:', error);
    } finally {
      setIsUnlocking(false);
    }
  };

  return (
    <div
      className="w-96 h-full overflow-y-auto relative bg-bg-secondary"
      style={{
        borderLeft: `4px solid ${color}`,
        backgroundImage: `linear-gradient(90deg, ${color}08 0%, ${color}03 50%, transparent 100%)`,
        boxShadow: `inset 4px 0 20px ${color}20`,
      }}
    >
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            {category && (
              <div
                className="text-4xl p-2 rounded-lg"
                style={{
                  backgroundColor: `${color}20`,
                  border: `2px solid ${color}40`,
                }}
              >
                {category.icon}
              </div>
            )}
            <div>
              <h2 className="text-xl font-display text-accent-primary">{skill.name}</h2>
              <p className="text-sm text-text-tertiary">{category?.name || 'Unknown Category'}</p>
            </div>
          </div>
          <GlassButton
            variant="secondary"
            onClick={onClose}
            className="text-xl leading-none px-2 py-1"
          >
            ×
          </GlassButton>
        </div>

        {/* Status indicators */}
        <div className="flex gap-2">
          {/* Tier badge */}
          <div
            className="px-3 py-1 rounded-full text-xs font-medium"
            style={{
              backgroundColor: `${tierColor}30`,
              color: tierColor,
              border: `1px solid ${tierColor}60`,
            }}
          >
            {tierLabel}
          </div>

          {/* Node type badge */}
          <div
            className="px-3 py-1 rounded-full text-xs font-medium"
            style={{
              backgroundColor: `${color}30`,
              color: '#fff',
              border: `1px solid ${color}60`,
            }}
          >
            {skill.nodeType === 'sun' && '☀️ Sun'}
            {skill.nodeType === 'planet' && '🪐 Planet'}
            {skill.nodeType === 'moon' && '🌙 Moon'}
          </div>

          {/* Unlock status */}
          {!skill.unlocked && (
            <div className="px-3 py-1 rounded-full text-xs font-medium bg-danger/30 text-accent-danger border border-accent-danger/60">
              🔒 Locked
            </div>
          )}
        </div>

        {/* Description */}
        <GlassCard className="p-4">
          <p className="text-text-primary text-sm leading-relaxed">{skill.description}</p>
        </GlassCard>

        {/* Level and XP */}
        {skill.unlocked && (
          <GlassCard className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-text-primary font-medium">Level</span>
              <span
                className="text-2xl font-display"
                style={{ color: color }}
              >
                {skill.level}
              </span>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-text-secondary text-sm">Experience</span>
                <span className="text-text-primary text-sm">
                  {skill.xp} / {skill.maxXP} XP
                </span>
              </div>
              <div className="w-full h-3 bg-glass-dark rounded-full overflow-hidden">
                <div
                  className="h-full transition-all duration-500 rounded-full"
                  style={{
                    width: `${progressPercent}%`,
                    background: `linear-gradient(90deg, ${color}, ${color}CC)`,
                    boxShadow: `0 0 10px ${color}80`,
                  }}
                />
              </div>
              <div className="text-xs text-text-tertiary text-right mt-1">
                {progressPercent.toFixed(1)}%
              </div>
            </div>
          </GlassCard>
        )}

        {/* Prerequisite */}
        {skill.prerequisite && (
          <GlassCard className="p-4">
            <h3 className="text-sm font-medium text-text-primary mb-2">Prerequisites</h3>
            <div className="flex items-center gap-2 text-text-secondary text-sm">
              <span>🔗</span>
              <span>Requires: {skill.prerequisite}</span>
            </div>
          </GlassCard>
        )}

        {/* Tool call reward */}
        {skill.toolCallReward && (
          <GlassCard className="p-4">
            <h3 className="text-sm font-medium text-text-primary mb-2">Reward</h3>
            <div
              className="flex items-center gap-2 p-2 rounded-lg text-sm"
              style={{
                backgroundColor: `${color}15`,
                border: `1px solid ${color}30`,
              }}
            >
              <span className="text-lg">🎁</span>
              <div>
                <div className="text-accent-primary font-mono text-xs">
                  {skill.toolCallReward}()
                </div>
                <div className="text-text-tertiary text-xs">
                  Unlocked at max level
                </div>
              </div>
            </div>
          </GlassCard>
        )}

        {/* Evidence */}
        {skill.evidence && skill.evidence.length > 0 && (
          <GlassCard className="p-4">
            <h3 className="text-sm font-medium text-text-primary mb-3">
              Evidence ({skill.evidence.length})
            </h3>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {skill.evidence.map((evidence, index) => {
                // Handle both old format (string) and new format (object)
                const blockId = typeof evidence === 'string' ? evidence : evidence.block_id;
                const description = typeof evidence === 'object' ? evidence.description : null;
                const xpGained = typeof evidence === 'object' ? evidence.xp_gained : null;

                return (
                  <div
                    key={index}
                    className="text-xs p-2 bg-glass-dark rounded space-y-1"
                  >
                    <div className="font-mono text-text-tertiary">{blockId}</div>
                    {description && (
                      <div className="text-text-secondary">{description}</div>
                    )}
                    {xpGained !== null && (
                      <div className="text-accent-primary">+{xpGained} XP</div>
                    )}
                  </div>
                );
              })}
            </div>
          </GlassCard>
        )}

        {/* Stats summary */}
        <GlassCard className="p-4">
          <h3 className="text-sm font-medium text-text-primary mb-3">Stats</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-text-tertiary mb-1">Node Type</div>
              <div className="text-text-primary capitalize">{skill.nodeType}</div>
            </div>
            <div>
              <div className="text-text-tertiary mb-1">Tier</div>
              <div className="text-text-primary">{tierLabel}</div>
            </div>
            <div>
              <div className="text-text-tertiary mb-1">Max XP</div>
              <div className="text-text-primary">{skill.maxXP}</div>
            </div>
            <div>
              <div className="text-text-tertiary mb-1">Status</div>
              <div className="text-text-primary">
                {skill.unlocked ? '✅ Unlocked' : '🔒 Locked'}
              </div>
            </div>
          </div>
        </GlassCard>

        {/* Unlock section */}
        {!skill.unlocked && (
          <GlassCard className="p-4 space-y-3">
            <h3 className="text-sm font-medium text-text-primary">Unlock Requirements</h3>

            {parentSkill ? (
              <>
                <div className="text-sm text-text-secondary">
                  Parent skill: <span className="text-accent-primary font-medium">{parentSkill.name}</span>
                </div>
                <div className="text-sm text-text-secondary">
                  Required XP: <span className="text-accent-primary font-medium">{unlockThreshold} XP</span>
                </div>
                <div className="text-sm text-text-secondary">
                  Current XP: <span className="text-accent-primary font-medium">{parentSkill.xp} XP</span>
                </div>

                {canUnlock ? (
                  <GlassButton
                    variant="primary"
                    className="w-full"
                    onClick={handleUnlock}
                    disabled={isUnlocking}
                  >
                    {isUnlocking ? 'Unlocking...' : '🔓 Unlock This Skill'}
                  </GlassButton>
                ) : (
                  <GlassButton variant="primary" className="w-full" disabled>
                    {parentSkill.unlocked
                      ? `Need ${unlockThreshold - parentSkill.xp} more XP in ${parentSkill.name}`
                      : `Unlock ${parentSkill.name} first`
                    }
                  </GlassButton>
                )}
              </>
            ) : (
              <div className="text-sm text-text-secondary">
                This skill should be unlocked by default.
              </div>
            )}
          </GlassCard>
        )}

        {skill.level === 100 && (
          <div
            className="p-4 rounded-lg text-center"
            style={{
              background: `linear-gradient(135deg, ${color}20, ${color}10)`,
              border: `2px solid ${color}40`,
            }}
          >
            <div className="text-3xl mb-2">🏆</div>
            <div className="text-lg font-display" style={{ color: color }}>
              Mastered!
            </div>
            {skill.toolCallReward && (
              <div className="text-xs text-text-secondary mt-1">
                Tool unlocked: <span className="font-mono text-accent-primary">{skill.toolCallReward}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
});

SkillDetailsPanel.displayName = 'SkillDetailsPanel';
