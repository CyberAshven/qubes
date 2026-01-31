import React from 'react';
import { XPToastContainer } from './XPToast';
import { LevelUpModal } from './LevelUpModal';
import { SkillUnlockOverlay } from './SkillUnlockOverlay';
import { MilestonePopupContainer } from './MilestoneTracker';

/**
 * CelebrationOverlay - Renders all celebration UI components
 *
 * Add this component to your app's root to enable celebrations.
 * It will render XP toasts, level-up modals, skill unlock notifications,
 * and milestone popups based on events triggered through CelebrationContext.
 */
export const CelebrationOverlay: React.FC = () => {
  return (
    <>
      {/* XP gain toasts - bottom right corner */}
      <XPToastContainer />

      {/* Skill unlock notifications - top center */}
      <SkillUnlockOverlay />

      {/* Level-up modal - center screen with confetti */}
      <LevelUpModal />

      {/* Milestone popups - center screen */}
      <MilestonePopupContainer />
    </>
  );
};

export default CelebrationOverlay;
