// Celebration components
export { CelebrationOverlay } from './CelebrationOverlay';
export { XPToastContainer } from './XPToast';
export { LevelUpModal } from './LevelUpModal';
export { SkillUnlockOverlay } from './SkillUnlockOverlay';
export { ConfettiExplosion } from './ConfettiExplosion';
export { ProgressRing } from './ProgressRing';
export { MilestonePopupContainer, useMilestoneChecker, MILESTONES } from './MilestoneTracker';

// Re-export context and hook
export { useCelebration, CelebrationProvider } from '../../contexts/CelebrationContext';
export type {
  XPGainEvent,
  LevelUpEvent,
  SkillUnlockEvent,
  MilestoneEvent,
  CelebrationSettings,
} from '../../contexts/CelebrationContext';
