import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useCelebration, MilestoneEvent } from '../../contexts/CelebrationContext';
import { GlassCard } from '../glass';
import { useCelebrationAudio } from '../../hooks/useCelebrationAudio';

// Milestone definitions
export const MILESTONES = {
  first_xp: {
    title: 'First XP!',
    description: 'You earned your first experience point.',
    icon: '\uD83C\uDF31', // seedling
  },
  first_level_up: {
    title: 'First Level Up!',
    description: 'Your first skill reached a new level.',
    icon: '\uD83D\uDCC8', // chart increasing
  },
  first_mastery: {
    title: 'First Mastery!',
    description: 'You maxed out a skill for the first time.',
    icon: '\uD83C\uDFC6', // trophy
  },
  category_complete: {
    title: 'Category Master!',
    description: 'You completed all skills in a category.',
    icon: '\uD83D\uDC51', // crown
  },
  total_xp_100: {
    title: 'Century Club',
    description: 'You earned 100 total XP.',
    icon: '\uD83D\uDCAF', // 100
  },
  total_xp_500: {
    title: 'XP Collector',
    description: 'You earned 500 total XP.',
    icon: '\uD83C\uDFAF', // target
  },
  total_xp_1000: {
    title: 'XP Enthusiast',
    description: 'You earned 1,000 total XP.',
    icon: '\uD83C\uDF1F', // glowing star
  },
  total_xp_5000: {
    title: 'XP Master',
    description: 'You earned 5,000 total XP.',
    icon: '\u2B50', // star
  },
  total_xp_10000: {
    title: 'XP Legend',
    description: 'You earned 10,000 total XP.',
    icon: '\uD83C\uDF20', // shooting star
  },
};

interface MilestonePopupProps {
  event: MilestoneEvent;
  onDismiss: () => void;
  reducedMotion: boolean;
}

const MilestonePopup: React.FC<MilestonePopupProps> = ({ event, onDismiss, reducedMotion }) => {
  const { playMilestoneSound } = useCelebrationAudio();

  useEffect(() => {
    playMilestoneSound();
  }, [playMilestoneSound]);

  return (
    <motion.div
      initial={reducedMotion ? { opacity: 0 } : { opacity: 0, scale: 0.8, y: 50 }}
      animate={reducedMotion ? { opacity: 1 } : { opacity: 1, scale: 1, y: 0 }}
      exit={reducedMotion ? { opacity: 0 } : { opacity: 0, scale: 0.8, y: -50 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      className="relative"
    >
      <GlassCard
        className="p-6 text-center cursor-pointer relative overflow-hidden"
        onClick={onDismiss}
      >
        {/* Background shimmer */}
        {!reducedMotion && (
          <motion.div
            className="absolute inset-0 opacity-20"
            style={{
              background: 'linear-gradient(45deg, transparent, #FFD700, transparent)',
              backgroundSize: '200% 200%',
            }}
            animate={{
              backgroundPosition: ['-200% 0', '200% 0'],
            }}
            transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          />
        )}

        <div className="relative z-10">
          {/* Icon */}
          <motion.div
            className="text-6xl mb-4"
            animate={reducedMotion ? {} : { scale: [1, 1.2, 1], rotate: [0, 10, -10, 0] }}
            transition={{ duration: 0.5 }}
          >
            {event.icon}
          </motion.div>

          {/* Title */}
          <h3 className="text-xl font-display text-accent-primary mb-2">
            {event.title}
          </h3>

          {/* Description */}
          <p className="text-text-secondary text-sm">
            {event.description}
          </p>

          {/* Dismiss hint */}
          <p className="text-text-tertiary text-xs mt-4">
            Click to dismiss
          </p>
        </div>
      </GlassCard>
    </motion.div>
  );
};

export const MilestonePopupContainer: React.FC = () => {
  const { milestones, dismissMilestone, settings } = useCelebration();

  if (!settings.enabled || milestones.length === 0) {
    return null;
  }

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
      {/* Backdrop */}
      <motion.div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={() => dismissMilestone(milestones[0].id)}
      />

      <AnimatePresence mode="wait">
        {milestones.length > 0 && (
          <MilestonePopup
            key={milestones[0].id}
            event={milestones[0]}
            onDismiss={() => dismissMilestone(milestones[0].id)}
            reducedMotion={settings.reducedMotion}
          />
        )}
      </AnimatePresence>
    </div>
  );
};

// Hook to check and trigger milestones
interface Skill {
  id: string;
  level: number;
  xp: number;
  [key: string]: unknown;
}

export const useMilestoneChecker = (totalXP: number, skills: Skill[]) => {
  const { triggerMilestone } = useCelebration();
  const checkedRef = useRef<Set<string>>(new Set());

  // Load checked milestones from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('checked_milestones');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        checkedRef.current = new Set(parsed);
      } catch {
        // Ignore parse errors
      }
    }
  }, []);

  useEffect(() => {
    const saveChecked = () => {
      localStorage.setItem('checked_milestones', JSON.stringify([...checkedRef.current]));
    };

    // Check XP milestones
    const xpMilestones = [
      { threshold: 100, key: 'total_xp_100' },
      { threshold: 500, key: 'total_xp_500' },
      { threshold: 1000, key: 'total_xp_1000' },
      { threshold: 5000, key: 'total_xp_5000' },
      { threshold: 10000, key: 'total_xp_10000' },
    ];

    xpMilestones.forEach(({ threshold, key }) => {
      if (totalXP >= threshold && !checkedRef.current.has(key)) {
        checkedRef.current.add(key);
        saveChecked();
        const milestone = MILESTONES[key as keyof typeof MILESTONES];
        triggerMilestone({
          qubeId: '',
          type: 'total_xp_milestone',
          title: milestone.title,
          description: milestone.description,
          icon: milestone.icon,
        });
      }
    });

    // Check first XP
    if (totalXP > 0 && !checkedRef.current.has('first_xp')) {
      checkedRef.current.add('first_xp');
      saveChecked();
      triggerMilestone({
        qubeId: '',
        type: 'first_xp',
        ...MILESTONES.first_xp,
      });
    }

    // Check first mastery
    const masteredSkill = skills.find(s => s.level >= 100);
    if (masteredSkill && !checkedRef.current.has('first_mastery')) {
      checkedRef.current.add('first_mastery');
      saveChecked();
      triggerMilestone({
        qubeId: '',
        type: 'first_mastery',
        ...MILESTONES.first_mastery,
      });
    }

    // Check first level up
    const leveledSkill = skills.find(s => s.level > 0);
    if (leveledSkill && !checkedRef.current.has('first_level_up')) {
      checkedRef.current.add('first_level_up');
      saveChecked();
      triggerMilestone({
        qubeId: '',
        type: 'first_level_up',
        ...MILESTONES.first_level_up,
      });
    }
  }, [totalXP, skills, triggerMilestone]);
};

export default MilestonePopupContainer;
