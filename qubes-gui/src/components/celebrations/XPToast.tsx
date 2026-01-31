import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useCelebration, XPGainEvent } from '../../contexts/CelebrationContext';
import { useCelebrationAudio } from '../../hooks/useCelebrationAudio';

// Format XP value for display
const formatXP = (xp: number): string => {
  const rounded = Math.round(xp * 10) / 10;
  return Number.isInteger(rounded) ? rounded.toString() : rounded.toFixed(1);
};

interface XPToastItemProps {
  event: XPGainEvent;
  onDismiss: () => void;
  reducedMotion: boolean;
}

const XPToastItem: React.FC<XPToastItemProps> = ({ event, onDismiss, reducedMotion }) => {
  const { playXPGainSound } = useCelebrationAudio();
  const progressPercent = Math.min(100, (event.newXP / event.maxXP) * 100);
  const isLevelUp = event.newLevel && event.previousLevel && event.newLevel > event.previousLevel;

  useEffect(() => {
    playXPGainSound();
  }, [playXPGainSound]);

  return (
    <motion.div
      initial={reducedMotion ? { opacity: 0 } : { opacity: 0, x: 100, scale: 0.8 }}
      animate={reducedMotion ? { opacity: 1 } : { opacity: 1, x: 0, scale: 1 }}
      exit={reducedMotion ? { opacity: 0 } : { opacity: 0, x: 100, scale: 0.8 }}
      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
      className="relative overflow-hidden rounded-xl backdrop-blur-md cursor-pointer"
      style={{
        background: `linear-gradient(135deg, ${event.categoryColor}20, ${event.categoryColor}10)`,
        border: `2px solid ${event.categoryColor}60`,
        boxShadow: `0 4px 20px ${event.categoryColor}30, inset 0 0 20px ${event.categoryColor}10`,
      }}
      onClick={onDismiss}
    >
      {/* Glow effect */}
      <div
        className="absolute inset-0 opacity-30"
        style={{
          background: `radial-gradient(circle at 20% 50%, ${event.categoryColor}40, transparent 60%)`,
        }}
      />

      <div className="relative p-4 flex items-center gap-3">
        {/* Skill Icon */}
        <div
          className="text-3xl w-12 h-12 flex items-center justify-center rounded-lg"
          style={{
            background: `${event.categoryColor}30`,
            border: `1px solid ${event.categoryColor}50`,
          }}
        >
          {event.skillIcon}
        </div>

        {/* XP Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-text-primary truncate">
              {event.skillName}
            </span>
            {isLevelUp && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-accent-primary/30 text-accent-primary animate-pulse">
                Level Up!
              </span>
            )}
          </div>

          {/* XP Amount */}
          <div className="flex items-center gap-2 mt-1">
            <motion.span
              className="text-lg font-bold"
              style={{ color: event.categoryColor }}
              initial={reducedMotion ? {} : { scale: 1.5 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 300 }}
            >
              +{formatXP(event.xpAmount)} XP
            </motion.span>
            <span className="text-xs text-text-secondary">
              ({formatXP(event.newXP)}/{event.maxXP})
            </span>
          </div>

          {/* Progress bar */}
          <div className="mt-2 h-1.5 bg-glass-dark rounded-full overflow-hidden">
            <motion.div
              className="h-full rounded-full"
              style={{
                background: `linear-gradient(90deg, ${event.categoryColor}, ${event.categoryColor}AA)`,
              }}
              initial={{ width: `${Math.max(0, progressPercent - (event.xpAmount / event.maxXP) * 100)}%` }}
              animate={{ width: `${progressPercent}%` }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
            />
          </div>
        </div>
      </div>

      {/* Shine animation */}
      {!reducedMotion && (
        <motion.div
          className="absolute inset-0 pointer-events-none"
          initial={{ x: '-100%' }}
          animate={{ x: '200%' }}
          transition={{ duration: 1, ease: 'easeInOut' }}
          style={{
            background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent)',
            width: '50%',
          }}
        />
      )}
    </motion.div>
  );
};

export const XPToastContainer: React.FC = () => {
  const { xpGains, dismissXPGain, settings } = useCelebration();

  if (!settings.enabled || !settings.xpToasts || xpGains.length === 0) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2 max-w-sm">
      <AnimatePresence mode="popLayout">
        {xpGains.slice(-5).map(event => (
          <XPToastItem
            key={event.id}
            event={event}
            onDismiss={() => dismissXPGain(event.id)}
            reducedMotion={settings.reducedMotion}
          />
        ))}
      </AnimatePresence>
    </div>
  );
};

export default XPToastContainer;
