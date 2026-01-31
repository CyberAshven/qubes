import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useCelebration, SkillUnlockEvent } from '../../contexts/CelebrationContext';
import { useCelebrationAudio } from '../../hooks/useCelebrationAudio';

interface UnlockItemProps {
  event: SkillUnlockEvent;
  onDismiss: () => void;
  reducedMotion: boolean;
}

const UnlockItem: React.FC<UnlockItemProps> = ({ event, onDismiss, reducedMotion }) => {
  const { playUnlockSound } = useCelebrationAudio();

  useEffect(() => {
    playUnlockSound();
  }, [playUnlockSound]);

  const getNodeEmoji = () => {
    switch (event.nodeType) {
      case 'sun': return '\u2600\uFE0F'; // sun
      case 'planet': return '\uD83E\uDE90'; // ringed planet
      case 'moon': return '\uD83C\uDF19'; // crescent moon
    }
  };

  return (
    <motion.div
      initial={reducedMotion ? { opacity: 0 } : { opacity: 0, y: -50, scale: 0.8 }}
      animate={reducedMotion ? { opacity: 1 } : { opacity: 1, y: 0, scale: 1 }}
      exit={reducedMotion ? { opacity: 0 } : { opacity: 0, y: -20, scale: 0.9 }}
      transition={{ type: 'spring', stiffness: 400, damping: 25 }}
      className="relative rounded-xl overflow-hidden cursor-pointer"
      style={{
        background: `linear-gradient(135deg, ${event.categoryColor}30, ${event.categoryColor}15)`,
        border: `2px solid ${event.categoryColor}80`,
        boxShadow: `0 0 40px ${event.categoryColor}40, 0 10px 30px rgba(0,0,0,0.3)`,
      }}
      onClick={onDismiss}
    >
      {/* Lock breaking animation */}
      {!reducedMotion && (
        <motion.div
          className="absolute inset-0 flex items-center justify-center pointer-events-none"
          initial={{ opacity: 1 }}
          animate={{ opacity: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
        >
          <motion.span
            className="text-6xl"
            initial={{ scale: 1 }}
            animate={{ scale: [1, 1.5, 0], rotate: [0, 0, 45] }}
            transition={{ duration: 0.5, times: [0, 0.3, 1] }}
          >
            &#128275;
          </motion.span>
        </motion.div>
      )}

      <div className="relative p-5 flex items-center gap-4">
        {/* Icon */}
        <motion.div
          className="text-4xl"
          animate={reducedMotion ? {} : { rotate: [0, -10, 10, 0] }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          {event.skillIcon}
        </motion.div>

        <div className="flex-1">
          {/* Title */}
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-bold uppercase tracking-wider" style={{ color: event.categoryColor }}>
              {getNodeEmoji()} Skill Unlocked!
            </span>
          </div>

          {/* Skill name */}
          <div className="text-lg font-medium text-text-primary">
            {event.skillName}
          </div>

          {/* Parent info */}
          {event.parentSkillName && (
            <div className="text-sm text-text-secondary mt-1">
              Unlocked from {event.parentSkillName}
            </div>
          )}
        </div>

        {/* Sparkle effect */}
        {!reducedMotion && (
          <motion.div
            className="text-2xl"
            animate={{ scale: [1, 1.2, 1], opacity: [1, 0.8, 1] }}
            transition={{ duration: 1, repeat: 3 }}
          >
            &#10024;
          </motion.div>
        )}
      </div>

      {/* Progress bar countdown (auto-dismiss indicator) */}
      <motion.div
        className="h-1"
        style={{ background: event.categoryColor }}
        initial={{ width: '100%' }}
        animate={{ width: '0%' }}
        transition={{ duration: 5, ease: 'linear' }}
      />
    </motion.div>
  );
};

export const SkillUnlockOverlay: React.FC = () => {
  const { skillUnlocks, dismissSkillUnlock, settings } = useCelebration();

  if (!settings.enabled || !settings.unlockAnimations || skillUnlocks.length === 0) {
    return null;
  }

  return (
    <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50 space-y-2 w-full max-w-md px-4">
      <AnimatePresence mode="popLayout">
        {skillUnlocks.slice(-3).map(event => (
          <UnlockItem
            key={event.id}
            event={event}
            onDismiss={() => dismissSkillUnlock(event.id)}
            reducedMotion={settings.reducedMotion}
          />
        ))}
      </AnimatePresence>
    </div>
  );
};

export default SkillUnlockOverlay;
