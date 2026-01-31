import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useCelebration, LevelUpEvent } from '../../contexts/CelebrationContext';
import { GlassButton } from '../glass';
import { ConfettiExplosion } from './ConfettiExplosion';
import { useCelebrationAudio } from '../../hooks/useCelebrationAudio';

interface LevelUpModalContentProps {
  event: LevelUpEvent;
  onClose: () => void;
  reducedMotion: boolean;
  showConfetti: boolean;
}

const LevelUpModalContent: React.FC<LevelUpModalContentProps> = ({
  event,
  onClose,
  reducedMotion,
  showConfetti,
}) => {
  const { playLevelUpSound, playMasterySound } = useCelebrationAudio();

  useEffect(() => {
    if (event.maxedOut) {
      playMasterySound();
    } else {
      playLevelUpSound();
    }
  }, [event.maxedOut, playLevelUpSound, playMasterySound]);

  // Node type specific styling
  const getNodeTypeStyle = () => {
    switch (event.nodeType) {
      case 'sun':
        return {
          size: 'text-8xl',
          title: 'SUN LEVEL UP!',
          subtitle: 'Major milestone achieved!',
          glowSize: 150,
        };
      case 'planet':
        return {
          size: 'text-6xl',
          title: 'PLANET LEVEL UP!',
          subtitle: 'Great progress!',
          glowSize: 100,
        };
      case 'moon':
        return {
          size: 'text-5xl',
          title: 'MOON LEVEL UP!',
          subtitle: 'Keep it up!',
          glowSize: 60,
        };
    }
  };

  const nodeStyle = getNodeTypeStyle();

  return (
    <>
      {/* Backdrop */}
      <motion.div
        className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      />

      {/* Confetti */}
      {showConfetti && !reducedMotion && (
        <ConfettiExplosion color={event.categoryColor} />
      )}

      {/* Modal */}
      <motion.div
        className="fixed inset-0 flex items-center justify-center z-50 p-4"
        initial={reducedMotion ? { opacity: 0 } : { opacity: 0, scale: 0.8 }}
        animate={reducedMotion ? { opacity: 1 } : { opacity: 1, scale: 1 }}
        exit={reducedMotion ? { opacity: 0 } : { opacity: 0, scale: 0.8 }}
        transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      >
        <div
          className="relative max-w-md w-full rounded-2xl overflow-hidden"
          style={{
            background: `linear-gradient(135deg, ${event.categoryColor}30 0%, ${event.categoryColor}10 100%)`,
            border: `3px solid ${event.categoryColor}80`,
            boxShadow: `
              0 0 ${nodeStyle.glowSize}px ${event.categoryColor}60,
              0 20px 60px rgba(0,0,0,0.5),
              inset 0 0 40px ${event.categoryColor}20
            `,
          }}
          onClick={e => e.stopPropagation()}
        >
          {/* Animated background rays */}
          {!reducedMotion && (
            <div className="absolute inset-0 overflow-hidden">
              <motion.div
                className="absolute inset-0"
                animate={{ rotate: 360 }}
                transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
                style={{
                  background: `conic-gradient(from 0deg, transparent, ${event.categoryColor}20, transparent, ${event.categoryColor}20, transparent)`,
                }}
              />
            </div>
          )}

          <div className="relative p-8 text-center">
            {/* Icon with glow */}
            <motion.div
              className={`${nodeStyle.size} mb-4`}
              animate={reducedMotion ? {} : { scale: [1, 1.1, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              <div
                className="inline-block"
                style={{
                  filter: `drop-shadow(0 0 20px ${event.categoryColor})`,
                }}
              >
                {event.skillIcon}
              </div>
            </motion.div>

            {/* Title */}
            <motion.h2
              className="text-3xl font-display mb-2"
              style={{ color: event.categoryColor }}
              initial={reducedMotion ? {} : { y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2 }}
            >
              {event.maxedOut ? 'MASTERY ACHIEVED!' : nodeStyle.title}
            </motion.h2>

            {/* Skill name */}
            <motion.p
              className="text-xl text-text-primary mb-1"
              initial={reducedMotion ? {} : { y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.3 }}
            >
              {event.skillName}
            </motion.p>

            {/* Level */}
            <motion.div
              className="text-6xl font-bold my-6"
              style={{ color: event.categoryColor }}
              initial={reducedMotion ? {} : { scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.4, type: 'spring', stiffness: 200 }}
            >
              {event.maxedOut ? (
                <span className="text-7xl">100</span>
              ) : (
                <>Level {event.newLevel}</>
              )}
            </motion.div>

            {/* Subtitle */}
            <motion.p
              className="text-text-secondary mb-6"
              initial={reducedMotion ? {} : { y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              {event.maxedOut ? 'You have mastered this skill!' : nodeStyle.subtitle}
            </motion.p>

            {/* Mastery badge */}
            {event.maxedOut && (
              <motion.div
                className="mb-6"
                initial={reducedMotion ? {} : { scale: 0, rotate: -180 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ delay: 0.6, type: 'spring' }}
              >
                <div
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-full"
                  style={{
                    background: `linear-gradient(135deg, #FFD700, #FFA500)`,
                    boxShadow: '0 0 30px #FFD70060',
                  }}
                >
                  <span className="text-2xl">&#127942;</span>
                  <span className="text-lg font-bold text-black">MASTER</span>
                </div>
              </motion.div>
            )}

            {/* Close button */}
            <motion.div
              initial={reducedMotion ? {} : { y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.7 }}
            >
              <GlassButton
                variant="primary"
                onClick={onClose}
                className="px-8 py-3 text-lg"
              >
                {event.maxedOut ? 'Celebrate!' : 'Continue'}
              </GlassButton>
            </motion.div>
          </div>
        </div>
      </motion.div>
    </>
  );
};

export const LevelUpModal: React.FC = () => {
  const { levelUps, dismissLevelUp, settings } = useCelebration();
  const [currentEvent, setCurrentEvent] = useState<LevelUpEvent | null>(null);

  // Show level-ups one at a time
  useEffect(() => {
    if (!currentEvent && levelUps.length > 0) {
      setCurrentEvent(levelUps[0]);
    }
  }, [levelUps, currentEvent]);

  const handleClose = () => {
    if (currentEvent) {
      dismissLevelUp(currentEvent.id);
      setCurrentEvent(null);
    }
  };

  if (!settings.enabled || !settings.levelUpModals || !currentEvent) {
    return null;
  }

  return (
    <AnimatePresence>
      <LevelUpModalContent
        event={currentEvent}
        onClose={handleClose}
        reducedMotion={settings.reducedMotion}
        showConfetti={settings.confetti}
      />
    </AnimatePresence>
  );
};

export default LevelUpModal;
