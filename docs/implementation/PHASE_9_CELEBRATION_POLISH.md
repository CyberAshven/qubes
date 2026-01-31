# Phase 9: Celebration & Polish - Implementation Blueprint

## Executive Summary

**Theme: Celebrate (Reward Progress and Delight Users)**

Phase 9 is a frontend-focused phase that adds satisfying visual and audio feedback throughout the skill tree system. When Qubes earn XP, users should feel that progress. When a Moon/Planet/Sun fills up, users should celebrate. This phase transforms functional skill progression into an emotionally engaging experience.

**Current State**: Skill tree is functional but lacks celebration feedback. No XP gain notifications, no level-up animations, no achievement sounds.

### Feature Summary

| Category | Count | Components |
|----------|-------|------------|
| Celebrations | 6 | XP Toast, Level-Up Modal, Skill Unlock Animation, Mastery Crown, Confetti System, Progress Pulse |
| Progress UI | 4 | Floating XP Indicator, XP Trickle Animation, Progress Ring, Milestone Tracker |
| Audio | 3 | XP Gain Sound, Level-Up Fanfare, Achievement Chime |
| Visual Effects | 4 | Particle System, Glow Effects, Shine Animation, Ripple Effect |
| **Total** | **17** | |

### Key Principles

1. **Non-Intrusive**: Celebrations should delight, not interrupt workflow
2. **Contextual**: Bigger achievements get bigger celebrations
3. **Opt-Out Friendly**: Users can disable celebrations in settings
4. **Performance-First**: Animations use GPU-accelerated CSS/Canvas
5. **Accessible**: Reduced motion support for all animations

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Task 9.1: Create Celebration Context](#task-91-create-celebration-context)
3. [Task 9.2: XP Gain Toast System](#task-92-xp-gain-toast-system)
4. [Task 9.3: Level-Up Modal](#task-93-level-up-modal)
5. [Task 9.4: Skill Unlock Animation](#task-94-skill-unlock-animation)
6. [Task 9.5: Confetti & Particle System](#task-95-confetti--particle-system)
7. [Task 9.6: XP Trickle Animation](#task-96-xp-trickle-animation)
8. [Task 9.7: Audio Feedback System](#task-97-audio-feedback-system)
9. [Task 9.8: Progress Ring Component](#task-98-progress-ring-component)
10. [Task 9.9: Milestone Tracker](#task-99-milestone-tracker)
11. [Task 9.10: Settings Integration](#task-910-settings-integration)
12. [Task 9.11: Backend Events](#task-911-backend-events)
13. [Task 9.12: Testing & Validation](#task-912-testing--validation)
14. [Files Modified Summary](#files-modified-summary)

---

## Prerequisites

### Existing Infrastructure

| Component | File | Status |
|-----------|------|--------|
| SkillsTab | `qubes-gui/src/components/tabs/SkillsTab.tsx` | Implemented |
| SunNode | `qubes-gui/src/components/skills/SunNode.tsx` | Implemented |
| PlanetNode | `qubes-gui/src/components/skills/PlanetNode.tsx` | Implemented |
| MoonNode | `qubes-gui/src/components/skills/MoonNode.tsx` | Implemented |
| SkillDetailsPanel | `qubes-gui/src/components/skills/SkillDetailsPanel.tsx` | Implemented |
| ChainStateContext | `qubes-gui/src/contexts/ChainStateContext.tsx` | Implemented |
| AudioContext | `qubes-gui/src/contexts/AudioContext.tsx` | Implemented |
| XP System | `ai/skill_scanner.py` | Implemented |

### From Previous Phases

1. **Phases 0-4**: Core skill tree structure
2. **Phases 5-8**: All tool definitions and XP routing

### Current Codebase State (as of Jan 2026)

#### Skill Tree UI (`qubes-gui/src/components/skills/`)
- **SunNode.tsx**: Has D3.js glow animation, XP bar, level display ✅
- **PlanetNode.tsx**: Basic node with XP progress ✅
- **MoonNode.tsx**: Basic node with XP progress ✅
- **SkillDetailsPanel.tsx**: Shows skill details, evidence, unlock button ✅
- **No celebration animations**: XP changes update silently
- **Action**: Add celebration overlays without modifying existing components

#### Audio System (`qubes-gui/src/contexts/AudioContext.tsx`)
- **Current**: Manages TTS audio playback
- **Status**: ✅ Implemented
- **Action**: Add new celebration audio hooks (separate from TTS)

#### Settings (`qubes-gui/src/components/tabs/SettingsTab.tsx`)
- **Current**: Voice settings, API keys, display preferences
- **Status**: ✅ Implemented
- **Action**: Add "Celebration Settings" section

#### No Existing Celebration UI
- **Toasts**: None implemented
- **Modals**: ExitConfirmDialog, PasswordPromptModal exist (patterns to follow)
- **Confetti**: None
- **Sound effects**: None for XP/skills
- **Action**: All celebration components are NEW

#### Dependencies
- **framer-motion**: May need to install (`npm install framer-motion`)
- **Audio files**: Need to create/source 5 celebration sounds

---

## Task 9.1: Create Celebration Context

### File: `qubes-gui/src/contexts/CelebrationContext.tsx` (NEW)

Create a context to manage celebration state and events across the app:

```typescript
import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';

// Types
export interface XPGainEvent {
  id: string;
  qubeId: string;
  skillId: string;
  skillName: string;
  skillIcon: string;
  categoryColor: string;
  xpAmount: number;
  newXP: number;
  maxXP: number;
  newLevel?: number;
  previousLevel?: number;
  timestamp: number;
}

export interface LevelUpEvent {
  id: string;
  qubeId: string;
  skillId: string;
  skillName: string;
  skillIcon: string;
  categoryColor: string;
  nodeType: 'sun' | 'planet' | 'moon';
  newLevel: number;
  maxedOut: boolean;  // True when level hits 100
  timestamp: number;
}

export interface SkillUnlockEvent {
  id: string;
  qubeId: string;
  skillId: string;
  skillName: string;
  skillIcon: string;
  categoryColor: string;
  nodeType: 'sun' | 'planet' | 'moon';
  parentSkillName?: string;
  timestamp: number;
}

export interface MilestoneEvent {
  id: string;
  qubeId: string;
  type: 'first_xp' | 'first_level_up' | 'first_mastery' | 'category_complete' | 'total_xp_milestone';
  title: string;
  description: string;
  icon: string;
  timestamp: number;
}

export interface CelebrationSettings {
  enabled: boolean;
  xpToasts: boolean;
  levelUpModals: boolean;
  unlockAnimations: boolean;
  confetti: boolean;
  sounds: boolean;
  reducedMotion: boolean;
}

interface CelebrationContextType {
  // Settings
  settings: CelebrationSettings;
  updateSettings: (settings: Partial<CelebrationSettings>) => void;

  // Event queues
  xpGains: XPGainEvent[];
  levelUps: LevelUpEvent[];
  skillUnlocks: SkillUnlockEvent[];
  milestones: MilestoneEvent[];

  // Event triggers (called by skill system)
  triggerXPGain: (event: Omit<XPGainEvent, 'id' | 'timestamp'>) => void;
  triggerLevelUp: (event: Omit<LevelUpEvent, 'id' | 'timestamp'>) => void;
  triggerSkillUnlock: (event: Omit<SkillUnlockEvent, 'id' | 'timestamp'>) => void;
  triggerMilestone: (event: Omit<MilestoneEvent, 'id' | 'timestamp'>) => void;

  // Event dismissal
  dismissXPGain: (id: string) => void;
  dismissLevelUp: (id: string) => void;
  dismissSkillUnlock: (id: string) => void;
  dismissMilestone: (id: string) => void;
  dismissAll: () => void;
}

const DEFAULT_SETTINGS: CelebrationSettings = {
  enabled: true,
  xpToasts: true,
  levelUpModals: true,
  unlockAnimations: true,
  confetti: true,
  sounds: true,
  reducedMotion: false,
};

const CelebrationContext = createContext<CelebrationContextType | null>(null);

export const CelebrationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Load settings from localStorage
  const [settings, setSettings] = useState<CelebrationSettings>(() => {
    const saved = localStorage.getItem('celebration_settings');
    if (saved) {
      try {
        return { ...DEFAULT_SETTINGS, ...JSON.parse(saved) };
      } catch {
        return DEFAULT_SETTINGS;
      }
    }
    return DEFAULT_SETTINGS;
  });

  // Check for system reduced motion preference
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (mediaQuery.matches) {
      setSettings(prev => ({ ...prev, reducedMotion: true }));
    }
  }, []);

  // Event queues
  const [xpGains, setXpGains] = useState<XPGainEvent[]>([]);
  const [levelUps, setLevelUps] = useState<LevelUpEvent[]>([]);
  const [skillUnlocks, setSkillUnlocks] = useState<SkillUnlockEvent[]>([]);
  const [milestones, setMilestones] = useState<MilestoneEvent[]>([]);

  // ID counter for unique event IDs
  const idCounter = useRef(0);
  const generateId = () => `celebration_${++idCounter.current}_${Date.now()}`;

  // Settings update
  const updateSettings = useCallback((newSettings: Partial<CelebrationSettings>) => {
    setSettings(prev => {
      const updated = { ...prev, ...newSettings };
      localStorage.setItem('celebration_settings', JSON.stringify(updated));
      return updated;
    });
  }, []);

  // Event triggers
  const triggerXPGain = useCallback((event: Omit<XPGainEvent, 'id' | 'timestamp'>) => {
    if (!settings.enabled || !settings.xpToasts) return;

    const fullEvent: XPGainEvent = {
      ...event,
      id: generateId(),
      timestamp: Date.now(),
    };

    setXpGains(prev => [...prev, fullEvent]);

    // Auto-dismiss after 3 seconds
    setTimeout(() => {
      setXpGains(prev => prev.filter(e => e.id !== fullEvent.id));
    }, 3000);
  }, [settings.enabled, settings.xpToasts]);

  const triggerLevelUp = useCallback((event: Omit<LevelUpEvent, 'id' | 'timestamp'>) => {
    if (!settings.enabled || !settings.levelUpModals) return;

    const fullEvent: LevelUpEvent = {
      ...event,
      id: generateId(),
      timestamp: Date.now(),
    };

    setLevelUps(prev => [...prev, fullEvent]);
  }, [settings.enabled, settings.levelUpModals]);

  const triggerSkillUnlock = useCallback((event: Omit<SkillUnlockEvent, 'id' | 'timestamp'>) => {
    if (!settings.enabled || !settings.unlockAnimations) return;

    const fullEvent: SkillUnlockEvent = {
      ...event,
      id: generateId(),
      timestamp: Date.now(),
    };

    setSkillUnlocks(prev => [...prev, fullEvent]);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      setSkillUnlocks(prev => prev.filter(e => e.id !== fullEvent.id));
    }, 5000);
  }, [settings.enabled, settings.unlockAnimations]);

  const triggerMilestone = useCallback((event: Omit<MilestoneEvent, 'id' | 'timestamp'>) => {
    if (!settings.enabled) return;

    const fullEvent: MilestoneEvent = {
      ...event,
      id: generateId(),
      timestamp: Date.now(),
    };

    setMilestones(prev => [...prev, fullEvent]);
  }, [settings.enabled]);

  // Dismissal functions
  const dismissXPGain = useCallback((id: string) => {
    setXpGains(prev => prev.filter(e => e.id !== id));
  }, []);

  const dismissLevelUp = useCallback((id: string) => {
    setLevelUps(prev => prev.filter(e => e.id !== id));
  }, []);

  const dismissSkillUnlock = useCallback((id: string) => {
    setSkillUnlocks(prev => prev.filter(e => e.id !== id));
  }, []);

  const dismissMilestone = useCallback((id: string) => {
    setMilestones(prev => prev.filter(e => e.id !== id));
  }, []);

  const dismissAll = useCallback(() => {
    setXpGains([]);
    setLevelUps([]);
    setSkillUnlocks([]);
    setMilestones([]);
  }, []);

  return (
    <CelebrationContext.Provider value={{
      settings,
      updateSettings,
      xpGains,
      levelUps,
      skillUnlocks,
      milestones,
      triggerXPGain,
      triggerLevelUp,
      triggerSkillUnlock,
      triggerMilestone,
      dismissXPGain,
      dismissLevelUp,
      dismissSkillUnlock,
      dismissMilestone,
      dismissAll,
    }}>
      {children}
    </CelebrationContext.Provider>
  );
};

export const useCelebration = () => {
  const context = useContext(CelebrationContext);
  if (!context) {
    throw new Error('useCelebration must be used within a CelebrationProvider');
  }
  return context;
};
```

### Integration in App.tsx

```typescript
// In qubes-gui/src/App.tsx
import { CelebrationProvider } from './contexts/CelebrationContext';

// Wrap the app:
<CelebrationProvider>
  {/* existing app content */}
</CelebrationProvider>
```

---

## Task 9.2: XP Gain Toast System

### File: `qubes-gui/src/components/celebrations/XPToast.tsx` (NEW)

A non-intrusive toast that appears when XP is gained:

```typescript
import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useCelebration, XPGainEvent } from '../../contexts/CelebrationContext';

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
  const progressPercent = (event.newXP / event.maxXP) * 100;

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
            {event.newLevel && event.previousLevel && event.newLevel > event.previousLevel && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-accent-primary/30 text-accent-primary">
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
```

### CSS Animations (add to global styles)

```css
/* In qubes-gui/src/index.css or tailwind config */
@keyframes xp-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.xp-toast-pulse {
  animation: xp-pulse 0.5s ease-in-out;
}
```

---

## Task 9.3: Level-Up Modal

### File: `qubes-gui/src/components/celebrations/LevelUpModal.tsx` (NEW)

A celebration modal when a skill levels up:

```typescript
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
                  <span className="text-2xl">🏆</span>
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
```

---

## Task 9.4: Skill Unlock Animation

### File: `qubes-gui/src/components/celebrations/SkillUnlockOverlay.tsx` (NEW)

An overlay that appears when a skill is unlocked:

```typescript
import React from 'react';
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

  React.useEffect(() => {
    playUnlockSound();
  }, [playUnlockSound]);

  const getNodeEmoji = () => {
    switch (event.nodeType) {
      case 'sun': return '☀️';
      case 'planet': return '🪐';
      case 'moon': return '🌙';
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
            🔓
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
            ✨
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
```

---

## Task 9.5: Confetti & Particle System

### File: `qubes-gui/src/components/celebrations/ConfettiExplosion.tsx` (NEW)

GPU-accelerated confetti using canvas:

```typescript
import React, { useEffect, useRef } from 'react';
import { useCelebration } from '../../contexts/CelebrationContext';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  color: string;
  rotation: number;
  rotationSpeed: number;
  scale: number;
  type: 'confetti' | 'star' | 'circle';
  life: number;
}

interface ConfettiExplosionProps {
  color?: string;
  particleCount?: number;
  duration?: number;
}

export const ConfettiExplosion: React.FC<ConfettiExplosionProps> = ({
  color = '#00ff88',
  particleCount = 100,
  duration = 3000,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { settings } = useCelebration();

  useEffect(() => {
    if (settings.reducedMotion || !settings.confetti) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    // Generate color palette based on main color
    const colors = [
      color,
      adjustColor(color, 30),
      adjustColor(color, -30),
      '#FFD700', // Gold
      '#FFFFFF', // White
    ];

    // Create particles
    const particles: Particle[] = [];
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;

    for (let i = 0; i < particleCount; i++) {
      const angle = (Math.PI * 2 * i) / particleCount + Math.random() * 0.5;
      const velocity = 5 + Math.random() * 10;

      particles.push({
        x: centerX,
        y: centerY,
        vx: Math.cos(angle) * velocity,
        vy: Math.sin(angle) * velocity - 5, // Initial upward bias
        color: colors[Math.floor(Math.random() * colors.length)],
        rotation: Math.random() * Math.PI * 2,
        rotationSpeed: (Math.random() - 0.5) * 0.2,
        scale: 0.5 + Math.random() * 0.5,
        type: ['confetti', 'star', 'circle'][Math.floor(Math.random() * 3)] as Particle['type'],
        life: 1,
      });
    }

    const startTime = Date.now();
    let animationId: number;

    const animate = () => {
      const elapsed = Date.now() - startTime;
      if (elapsed > duration) {
        return;
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      particles.forEach(particle => {
        // Update physics
        particle.vy += 0.15; // Gravity
        particle.x += particle.vx;
        particle.y += particle.vy;
        particle.rotation += particle.rotationSpeed;
        particle.vx *= 0.99; // Air resistance
        particle.life = Math.max(0, 1 - elapsed / duration);

        // Draw particle
        ctx.save();
        ctx.translate(particle.x, particle.y);
        ctx.rotate(particle.rotation);
        ctx.globalAlpha = particle.life;
        ctx.fillStyle = particle.color;

        const size = 10 * particle.scale;

        switch (particle.type) {
          case 'confetti':
            ctx.fillRect(-size / 2, -size / 4, size, size / 2);
            break;
          case 'star':
            drawStar(ctx, 0, 0, 5, size / 2, size / 4);
            break;
          case 'circle':
            ctx.beginPath();
            ctx.arc(0, 0, size / 3, 0, Math.PI * 2);
            ctx.fill();
            break;
        }

        ctx.restore();
      });

      animationId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
    };
  }, [color, particleCount, duration, settings.reducedMotion, settings.confetti]);

  if (settings.reducedMotion || !settings.confetti) {
    return null;
  }

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-[100]"
      style={{ mixBlendMode: 'screen' }}
    />
  );
};

// Helper to draw a star
function drawStar(ctx: CanvasRenderingContext2D, cx: number, cy: number, spikes: number, outerRadius: number, innerRadius: number) {
  let rot = (Math.PI / 2) * 3;
  let x = cx;
  let y = cy;
  const step = Math.PI / spikes;

  ctx.beginPath();
  ctx.moveTo(cx, cy - outerRadius);

  for (let i = 0; i < spikes; i++) {
    x = cx + Math.cos(rot) * outerRadius;
    y = cy + Math.sin(rot) * outerRadius;
    ctx.lineTo(x, y);
    rot += step;

    x = cx + Math.cos(rot) * innerRadius;
    y = cy + Math.sin(rot) * innerRadius;
    ctx.lineTo(x, y);
    rot += step;
  }

  ctx.lineTo(cx, cy - outerRadius);
  ctx.closePath();
  ctx.fill();
}

// Helper to adjust color brightness
function adjustColor(color: string, amount: number): string {
  const hex = color.replace('#', '');
  const r = Math.max(0, Math.min(255, parseInt(hex.substring(0, 2), 16) + amount));
  const g = Math.max(0, Math.min(255, parseInt(hex.substring(2, 4), 16) + amount));
  const b = Math.max(0, Math.min(255, parseInt(hex.substring(4, 6), 16) + amount));
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}
```

---

## Task 9.6: XP Trickle Animation

### File: `qubes-gui/src/components/celebrations/XPTrickleAnimation.tsx` (NEW)

Visual feedback showing XP flowing from Moon → Planet → Sun:

```typescript
import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useCelebration } from '../../contexts/CelebrationContext';

interface TrickleParticle {
  id: string;
  startX: number;
  startY: number;
  endX: number;
  endY: number;
  color: string;
  amount: number;
}

interface XPTrickleAnimationProps {
  // Source skill position (where XP was earned)
  sourceX: number;
  sourceY: number;
  // Target skill position (parent skill)
  targetX: number;
  targetY: number;
  // XP amount
  amount: number;
  // Category color
  color: string;
  // Callback when animation completes
  onComplete?: () => void;
}

export const XPTrickleAnimation: React.FC<XPTrickleAnimationProps> = ({
  sourceX,
  sourceY,
  targetX,
  targetY,
  amount,
  color,
  onComplete,
}) => {
  const { settings } = useCelebration();
  const [particles, setParticles] = useState<TrickleParticle[]>([]);

  useEffect(() => {
    if (settings.reducedMotion) {
      onComplete?.();
      return;
    }

    // Create multiple small particles
    const particleCount = Math.min(10, Math.ceil(amount * 2));
    const newParticles: TrickleParticle[] = [];

    for (let i = 0; i < particleCount; i++) {
      newParticles.push({
        id: `particle_${i}_${Date.now()}`,
        startX: sourceX + (Math.random() - 0.5) * 20,
        startY: sourceY + (Math.random() - 0.5) * 20,
        endX: targetX + (Math.random() - 0.5) * 10,
        endY: targetY + (Math.random() - 0.5) * 10,
        color,
        amount: amount / particleCount,
      });
    }

    setParticles(newParticles);

    // Clear after animation
    const timer = setTimeout(() => {
      setParticles([]);
      onComplete?.();
    }, 1000);

    return () => clearTimeout(timer);
  }, [sourceX, sourceY, targetX, targetY, amount, color, settings.reducedMotion, onComplete]);

  if (settings.reducedMotion || particles.length === 0) {
    return null;
  }

  return (
    <div className="fixed inset-0 pointer-events-none z-40">
      <AnimatePresence>
        {particles.map((particle, index) => (
          <motion.div
            key={particle.id}
            className="absolute w-3 h-3 rounded-full"
            style={{
              background: `radial-gradient(circle, ${particle.color}, ${particle.color}00)`,
              boxShadow: `0 0 10px ${particle.color}`,
            }}
            initial={{
              x: particle.startX,
              y: particle.startY,
              scale: 1,
              opacity: 1,
            }}
            animate={{
              x: particle.endX,
              y: particle.endY,
              scale: 0.5,
              opacity: 0,
            }}
            transition={{
              duration: 0.8,
              delay: index * 0.05,
              ease: [0.4, 0, 0.2, 1],
            }}
          />
        ))}
      </AnimatePresence>
    </div>
  );
};

// Hook to manage trickle animations
export const useXPTrickle = () => {
  const [trickles, setTrickles] = useState<XPTrickleAnimationProps[]>([]);

  const addTrickle = (trickle: Omit<XPTrickleAnimationProps, 'onComplete'>) => {
    const id = Date.now();
    setTrickles(prev => [
      ...prev,
      {
        ...trickle,
        onComplete: () => {
          setTrickles(prev => prev.filter((_, i) => i !== 0));
        },
      },
    ]);
  };

  return { trickles, addTrickle };
};
```

---

## Task 9.7: Audio Feedback System

### File: `qubes-gui/src/hooks/useCelebrationAudio.tsx` (NEW)

Audio hooks for celebration sounds:

```typescript
import { useCallback, useRef, useEffect } from 'react';
import { useCelebration } from '../contexts/CelebrationContext';

// Audio file URLs (these should be placed in public/audio/)
const AUDIO_FILES = {
  xpGain: '/audio/xp-gain.mp3',
  levelUp: '/audio/level-up.mp3',
  mastery: '/audio/mastery.mp3',
  unlock: '/audio/unlock.mp3',
  milestone: '/audio/milestone.mp3',
};

export const useCelebrationAudio = () => {
  const { settings } = useCelebration();
  const audioRefs = useRef<Record<string, HTMLAudioElement>>({});

  // Pre-load audio files
  useEffect(() => {
    if (typeof window === 'undefined') return;

    Object.entries(AUDIO_FILES).forEach(([key, url]) => {
      const audio = new Audio(url);
      audio.volume = 0.3;
      audio.preload = 'auto';
      audioRefs.current[key] = audio;
    });

    return () => {
      Object.values(audioRefs.current).forEach(audio => {
        audio.pause();
        audio.src = '';
      });
    };
  }, []);

  const playSound = useCallback((soundKey: keyof typeof AUDIO_FILES) => {
    if (!settings.enabled || !settings.sounds) return;

    const audio = audioRefs.current[soundKey];
    if (audio) {
      audio.currentTime = 0;
      audio.play().catch(() => {
        // Ignore autoplay errors (user hasn't interacted yet)
      });
    }
  }, [settings.enabled, settings.sounds]);

  const playXPGainSound = useCallback(() => {
    playSound('xpGain');
  }, [playSound]);

  const playLevelUpSound = useCallback(() => {
    playSound('levelUp');
  }, [playSound]);

  const playMasterySound = useCallback(() => {
    playSound('mastery');
  }, [playSound]);

  const playUnlockSound = useCallback(() => {
    playSound('unlock');
  }, [playSound]);

  const playMilestoneSound = useCallback(() => {
    playSound('milestone');
  }, [playSound]);

  return {
    playXPGainSound,
    playLevelUpSound,
    playMasterySound,
    playUnlockSound,
    playMilestoneSound,
  };
};
```

### Audio Files to Create

Create these audio files in `qubes-gui/public/audio/`:

| File | Description | Duration | Style |
|------|-------------|----------|-------|
| `xp-gain.mp3` | Soft chime | ~0.3s | Subtle, satisfying "ding" |
| `level-up.mp3` | Ascending tones | ~1s | Celebratory fanfare |
| `mastery.mp3` | Grand achievement | ~2s | Epic orchestral stinger |
| `unlock.mp3` | Lock click + shine | ~0.5s | Mechanical + magical |
| `milestone.mp3` | Achievement tone | ~1s | Proud, accomplished feel |

**Note**: Use royalty-free sounds from sources like Mixkit, Freesound, or generate with AI tools.

---

## Task 9.8: Progress Ring Component

### File: `qubes-gui/src/components/celebrations/ProgressRing.tsx` (NEW)

A circular progress indicator for skill nodes:

```typescript
import React from 'react';
import { motion } from 'framer-motion';
import { useCelebration } from '../../contexts/CelebrationContext';

interface ProgressRingProps {
  progress: number; // 0-100
  size: number;
  strokeWidth: number;
  color: string;
  backgroundColor?: string;
  animated?: boolean;
  showPercentage?: boolean;
  children?: React.ReactNode;
}

export const ProgressRing: React.FC<ProgressRingProps> = ({
  progress,
  size,
  strokeWidth,
  color,
  backgroundColor = 'rgba(255,255,255,0.1)',
  animated = true,
  showPercentage = false,
  children,
}) => {
  const { settings } = useCelebration();
  const shouldAnimate = animated && !settings.reducedMotion;

  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg
        width={size}
        height={size}
        className="transform -rotate-90"
      >
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={backgroundColor}
          strokeWidth={strokeWidth}
        />

        {/* Progress circle */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset }}
          transition={shouldAnimate ? { duration: 0.5, ease: 'easeOut' } : { duration: 0 }}
          style={{
            filter: `drop-shadow(0 0 4px ${color})`,
          }}
        />

        {/* Glow effect at progress tip */}
        {progress > 0 && progress < 100 && (
          <motion.circle
            cx={size / 2 + radius * Math.cos((progress / 100) * Math.PI * 2 - Math.PI / 2)}
            cy={size / 2 + radius * Math.sin((progress / 100) * Math.PI * 2 - Math.PI / 2)}
            r={strokeWidth / 2 + 2}
            fill={color}
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity: [0.5, 1, 0.5], scale: [1, 1.2, 1] }}
            transition={{ duration: 1, repeat: Infinity }}
            style={{
              filter: `blur(2px)`,
            }}
          />
        )}
      </svg>

      {/* Center content */}
      <div className="absolute inset-0 flex items-center justify-center">
        {showPercentage ? (
          <span className="text-sm font-bold" style={{ color }}>
            {Math.round(progress)}%
          </span>
        ) : (
          children
        )}
      </div>

      {/* Full completion sparkle */}
      {progress >= 100 && !settings.reducedMotion && (
        <motion.div
          className="absolute inset-0 flex items-center justify-center pointer-events-none"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: [0, 1, 0], scale: [0.8, 1.2, 0.8] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <div
            className="absolute w-full h-full rounded-full"
            style={{
              background: `radial-gradient(circle, ${color}40, transparent 70%)`,
            }}
          />
        </motion.div>
      )}
    </div>
  );
};
```

---

## Task 9.9: Milestone Tracker

### File: `qubes-gui/src/components/celebrations/MilestoneTracker.tsx` (NEW)

Track and display achievement milestones:

```typescript
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useCelebration, MilestoneEvent } from '../../contexts/CelebrationContext';
import { GlassCard } from '../glass';

// Milestone definitions
export const MILESTONES = {
  first_xp: {
    title: 'First XP!',
    description: 'You earned your first experience point.',
    icon: '🌱',
  },
  first_level_up: {
    title: 'First Level Up!',
    description: 'Your first skill reached a new level.',
    icon: '📈',
  },
  first_mastery: {
    title: 'First Mastery!',
    description: 'You maxed out a skill for the first time.',
    icon: '🏆',
  },
  category_complete: {
    title: 'Category Master!',
    description: 'You completed all skills in a category.',
    icon: '👑',
  },
  total_xp_100: {
    title: 'Century Club',
    description: 'You earned 100 total XP.',
    icon: '💯',
  },
  total_xp_500: {
    title: 'XP Collector',
    description: 'You earned 500 total XP.',
    icon: '🎯',
  },
  total_xp_1000: {
    title: 'XP Enthusiast',
    description: 'You earned 1,000 total XP.',
    icon: '🌟',
  },
  total_xp_5000: {
    title: 'XP Master',
    description: 'You earned 5,000 total XP.',
    icon: '⭐',
  },
  total_xp_10000: {
    title: 'XP Legend',
    description: 'You earned 10,000 total XP.',
    icon: '🌠',
  },
};

interface MilestonePopupProps {
  event: MilestoneEvent;
  onDismiss: () => void;
  reducedMotion: boolean;
}

const MilestonePopup: React.FC<MilestonePopupProps> = ({ event, onDismiss, reducedMotion }) => {
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
            animate={{
              background: [
                'linear-gradient(45deg, transparent, #FFD700, transparent)',
                'linear-gradient(45deg, transparent, #FFD700, transparent)',
              ],
              backgroundPosition: ['-200% 0', '200% 0'],
            }}
            transition={{ duration: 2, repeat: Infinity }}
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
export const useMilestoneChecker = (totalXP: number, skills: any[]) => {
  const { triggerMilestone } = useCelebration();
  const checkedRef = React.useRef<Set<string>>(new Set());

  React.useEffect(() => {
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
      triggerMilestone({
        qubeId: '',
        type: 'first_xp',
        ...MILESTONES.first_xp,
      });
    }

    // Check first mastery
    const masteredSkill = skills.find(s => s.level === 100);
    if (masteredSkill && !checkedRef.current.has('first_mastery')) {
      checkedRef.current.add('first_mastery');
      triggerMilestone({
        qubeId: '',
        type: 'first_mastery',
        ...MILESTONES.first_mastery,
      });
    }
  }, [totalXP, skills, triggerMilestone]);
};
```

---

## Task 9.10: Settings Integration

### File: Update `qubes-gui/src/components/tabs/SettingsTab.tsx`

Add celebration settings section:

```typescript
// Add this section to SettingsTab.tsx

import { useCelebration } from '../../contexts/CelebrationContext';

// Inside SettingsTab component:
const { settings: celebrationSettings, updateSettings: updateCelebrationSettings } = useCelebration();

// Add this JSX in the settings sections:

{/* Celebration Settings */}
<GlassCard className="p-6">
  <h3 className="text-lg font-display text-accent-primary mb-4 flex items-center gap-2">
    🎉 Celebration Settings
  </h3>

  <div className="space-y-4">
    {/* Master toggle */}
    <div className="flex items-center justify-between">
      <div>
        <div className="text-text-primary font-medium">Enable Celebrations</div>
        <div className="text-text-secondary text-sm">Show visual feedback for XP and level-ups</div>
      </div>
      <label className="relative inline-flex items-center cursor-pointer">
        <input
          type="checkbox"
          checked={celebrationSettings.enabled}
          onChange={(e) => updateCelebrationSettings({ enabled: e.target.checked })}
          className="sr-only peer"
        />
        <div className="w-11 h-6 bg-glass-dark rounded-full peer peer-checked:bg-accent-primary peer-checked:shadow-lg peer-checked:shadow-accent-primary/30 transition-all">
          <div className="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
        </div>
      </label>
    </div>

    {/* Sub-settings (only shown when enabled) */}
    {celebrationSettings.enabled && (
      <>
        <div className="border-t border-glass-border pt-4 space-y-3">
          {/* XP Toasts */}
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">XP Gain Notifications</span>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={celebrationSettings.xpToasts}
                onChange={(e) => updateCelebrationSettings({ xpToasts: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-glass-dark rounded-full peer peer-checked:bg-accent-primary/80 transition-all">
                <div className="absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-4" />
              </div>
            </label>
          </div>

          {/* Level-up modals */}
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">Level-Up Celebrations</span>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={celebrationSettings.levelUpModals}
                onChange={(e) => updateCelebrationSettings({ levelUpModals: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-glass-dark rounded-full peer peer-checked:bg-accent-primary/80 transition-all">
                <div className="absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-4" />
              </div>
            </label>
          </div>

          {/* Unlock animations */}
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">Skill Unlock Animations</span>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={celebrationSettings.unlockAnimations}
                onChange={(e) => updateCelebrationSettings({ unlockAnimations: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-glass-dark rounded-full peer peer-checked:bg-accent-primary/80 transition-all">
                <div className="absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-4" />
              </div>
            </label>
          </div>

          {/* Confetti */}
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">Confetti Effects</span>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={celebrationSettings.confetti}
                onChange={(e) => updateCelebrationSettings({ confetti: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-glass-dark rounded-full peer peer-checked:bg-accent-primary/80 transition-all">
                <div className="absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-4" />
              </div>
            </label>
          </div>

          {/* Sounds */}
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">Sound Effects</span>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={celebrationSettings.sounds}
                onChange={(e) => updateCelebrationSettings({ sounds: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-glass-dark rounded-full peer peer-checked:bg-accent-primary/80 transition-all">
                <div className="absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-4" />
              </div>
            </label>
          </div>

          {/* Reduced motion */}
          <div className="flex items-center justify-between">
            <div>
              <span className="text-text-secondary">Reduced Motion</span>
              <div className="text-text-tertiary text-xs">Disable animations for accessibility</div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={celebrationSettings.reducedMotion}
                onChange={(e) => updateCelebrationSettings({ reducedMotion: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-glass-dark rounded-full peer peer-checked:bg-accent-primary/80 transition-all">
                <div className="absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-4" />
              </div>
            </label>
          </div>
        </div>
      </>
    )}
  </div>
</GlassCard>
```

---

## Task 9.11: Backend Events

### File: `ai/skill_scanner.py`

Update to emit celebration events when XP is gained:

```python
# Add to skill_scanner.py

from typing import Optional, Dict, Any
import json

class SkillEvent:
    """Event emitted when skill progress changes."""

    XP_GAINED = "xp_gained"
    LEVEL_UP = "level_up"
    SKILL_UNLOCKED = "skill_unlocked"
    MASTERY_ACHIEVED = "mastery_achieved"

    def __init__(
        self,
        event_type: str,
        qube_id: str,
        skill_id: str,
        skill_name: str,
        skill_icon: str,
        category_color: str,
        node_type: str,
        data: Dict[str, Any]
    ):
        self.event_type = event_type
        self.qube_id = qube_id
        self.skill_id = skill_id
        self.skill_name = skill_name
        self.skill_icon = skill_icon
        self.category_color = category_color
        self.node_type = node_type
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "qube_id": self.qube_id,
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "skill_icon": self.skill_icon,
            "category_color": self.category_color,
            "node_type": self.node_type,
            **self.data
        }


# Update the award_skill_xp function to return events:

async def award_skill_xp(
    qube_id: str,
    skill_id: str,
    xp_amount: float,
    skills: List[Dict],
    skill_definitions: Dict
) -> tuple[List[Dict], List[SkillEvent]]:
    """
    Award XP to a skill and handle trickle-up.
    Returns updated skills list and list of events.
    """
    events: List[SkillEvent] = []

    # Find the skill
    skill = next((s for s in skills if s["id"] == skill_id), None)
    if not skill:
        return skills, events

    # Get skill definition for colors/icons
    skill_def = skill_definitions.get(skill_id, {})
    category_color = skill_def.get("category_color", "#00ff88")
    skill_icon = skill_def.get("icon", "🎯")

    # Store previous state
    previous_xp = skill.get("xp", 0)
    previous_level = skill.get("level", 0)

    # Add XP
    new_xp = previous_xp + xp_amount
    max_xp = skill.get("max_xp", 250)

    # Cap at max
    if new_xp > max_xp:
        new_xp = max_xp

    skill["xp"] = new_xp

    # Calculate new level (1 level per 1% of max_xp)
    new_level = min(100, int((new_xp / max_xp) * 100))
    skill["level"] = new_level

    # Emit XP gained event
    events.append(SkillEvent(
        event_type=SkillEvent.XP_GAINED,
        qube_id=qube_id,
        skill_id=skill_id,
        skill_name=skill.get("name", skill_id),
        skill_icon=skill_icon,
        category_color=category_color,
        node_type=skill.get("node_type", "moon"),
        data={
            "xp_amount": xp_amount,
            "new_xp": new_xp,
            "max_xp": max_xp,
            "previous_level": previous_level,
            "new_level": new_level,
        }
    ))

    # Check for level up
    if new_level > previous_level:
        events.append(SkillEvent(
            event_type=SkillEvent.LEVEL_UP,
            qube_id=qube_id,
            skill_id=skill_id,
            skill_name=skill.get("name", skill_id),
            skill_icon=skill_icon,
            category_color=category_color,
            node_type=skill.get("node_type", "moon"),
            data={
                "new_level": new_level,
                "maxed_out": new_level >= 100,
            }
        ))

    # Check for mastery
    if new_level >= 100 and previous_level < 100:
        events.append(SkillEvent(
            event_type=SkillEvent.MASTERY_ACHIEVED,
            qube_id=qube_id,
            skill_id=skill_id,
            skill_name=skill.get("name", skill_id),
            skill_icon=skill_icon,
            category_color=category_color,
            node_type=skill.get("node_type", "moon"),
            data={}
        ))

    # Handle XP trickle-up to parent
    parent_id = skill.get("parent_skill")
    if parent_id and xp_amount > 0:
        skills, parent_events = await award_skill_xp(
            qube_id=qube_id,
            skill_id=parent_id,
            xp_amount=xp_amount,  # Full trickle-up
            skills=skills,
            skill_definitions=skill_definitions
        )
        events.extend(parent_events)

    return skills, events
```

### File: `src-tauri/src/commands/skills.rs`

Update Tauri command to include events:

```rust
// Add to skills.rs

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct SkillEvent {
    pub event_type: String,
    pub qube_id: String,
    pub skill_id: String,
    pub skill_name: String,
    pub skill_icon: String,
    pub category_color: String,
    pub node_type: String,
    #[serde(flatten)]
    pub data: serde_json::Value,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SkillUpdateResponse {
    pub success: bool,
    pub skills: Vec<Skill>,
    pub events: Vec<SkillEvent>,
    pub error: Option<String>,
}

#[tauri::command]
pub async fn award_xp(
    state: State<'_, AppState>,
    user_id: String,
    qube_id: String,
    tool_name: String,
    success: bool,
) -> Result<SkillUpdateResponse, String> {
    // ... existing implementation ...

    // Include events in response
    Ok(SkillUpdateResponse {
        success: true,
        skills: updated_skills,
        events: skill_events,
        error: None,
    })
}
```

---

## Task 9.12: Testing & Validation

### Test Checklist

#### XP Toast Tests
- [ ] Toast appears when XP is gained
- [ ] Toast shows correct skill name and icon
- [ ] Toast shows correct XP amount
- [ ] Toast shows progress bar animation
- [ ] Toast auto-dismisses after 3 seconds
- [ ] Multiple toasts stack correctly (max 5)
- [ ] Click to dismiss works
- [ ] Respects celebration settings (off/on)
- [ ] Respects reduced motion setting

#### Level-Up Modal Tests
- [ ] Modal appears on level up
- [ ] Different styling for Sun/Planet/Moon
- [ ] Confetti plays (when enabled)
- [ ] Sound plays (when enabled)
- [ ] Mastery (level 100) shows special treatment
- [ ] Close button works
- [ ] Backdrop click closes
- [ ] Modal queue works (multiple level-ups)

#### Skill Unlock Tests
- [ ] Overlay appears when skill unlocks
- [ ] Shows lock-breaking animation
- [ ] Shows parent skill reference
- [ ] Auto-dismisses after 5 seconds
- [ ] Sound plays (when enabled)

#### Confetti Tests
- [ ] Confetti renders on canvas
- [ ] Colors match skill category
- [ ] Particles have physics (gravity, air resistance)
- [ ] Animation completes and cleans up
- [ ] No memory leaks on repeated triggers
- [ ] Disabled when reducedMotion is true

#### Audio Tests
- [ ] XP gain sound plays
- [ ] Level-up sound plays
- [ ] Mastery sound plays (different from level-up)
- [ ] Unlock sound plays
- [ ] Sounds respect volume settings
- [ ] No errors on rapid playback
- [ ] Graceful fallback if audio files missing

#### Settings Tests
- [ ] Master toggle disables all celebrations
- [ ] Individual toggles work correctly
- [ ] Settings persist in localStorage
- [ ] System reduced motion preference detected
- [ ] Settings update in real-time

#### Performance Tests
- [ ] No frame drops during confetti
- [ ] Animations smooth on low-end devices
- [ ] Memory usage stable after many celebrations
- [ ] Canvas properly disposed

---

## Files Modified Summary

### New Files (Frontend)

| File | Description |
|------|-------------|
| `qubes-gui/src/contexts/CelebrationContext.tsx` | Celebration state management |
| `qubes-gui/src/components/celebrations/XPToast.tsx` | XP gain notifications |
| `qubes-gui/src/components/celebrations/LevelUpModal.tsx` | Level-up celebration modal |
| `qubes-gui/src/components/celebrations/SkillUnlockOverlay.tsx` | Skill unlock overlay |
| `qubes-gui/src/components/celebrations/ConfettiExplosion.tsx` | Canvas-based confetti |
| `qubes-gui/src/components/celebrations/XPTrickleAnimation.tsx` | XP flow visualization |
| `qubes-gui/src/components/celebrations/ProgressRing.tsx` | Circular progress indicator |
| `qubes-gui/src/components/celebrations/MilestoneTracker.tsx` | Achievement milestones |
| `qubes-gui/src/hooks/useCelebrationAudio.tsx` | Audio playback hooks |
| `qubes-gui/public/audio/xp-gain.mp3` | XP gain sound |
| `qubes-gui/public/audio/level-up.mp3` | Level-up sound |
| `qubes-gui/public/audio/mastery.mp3` | Mastery sound |
| `qubes-gui/public/audio/unlock.mp3` | Unlock sound |
| `qubes-gui/public/audio/milestone.mp3` | Milestone sound |

### Modified Files

| File | Changes |
|------|---------|
| `qubes-gui/src/App.tsx` | Add CelebrationProvider |
| `qubes-gui/src/components/tabs/SettingsTab.tsx` | Add celebration settings UI |
| `qubes-gui/src/components/tabs/SkillsTab.tsx` | Integrate celebration triggers |
| `ai/skill_scanner.py` | Emit skill events |
| `src-tauri/src/commands/skills.rs` | Include events in response |

### Dependencies to Add

```json
// package.json
{
  "dependencies": {
    "framer-motion": "^10.16.0"
  }
}
```

---

## Implementation Order

1. **Task 9.1**: CelebrationContext (foundation)
2. **Task 9.7**: Audio system (needed by other components)
3. **Task 9.2**: XP Toast (most common celebration)
4. **Task 9.5**: Confetti (used by level-up modal)
5. **Task 9.3**: Level-Up Modal
6. **Task 9.4**: Skill Unlock Overlay
7. **Task 9.8**: Progress Ring
8. **Task 9.6**: XP Trickle Animation
9. **Task 9.9**: Milestone Tracker
10. **Task 9.10**: Settings Integration
11. **Task 9.11**: Backend Events
12. **Task 9.12**: Testing

---

## Notes

- **Framer Motion**: This phase assumes framer-motion is installed. If not, run `npm install framer-motion`.
- **Audio Files**: Placeholder audio files should be created or sourced from royalty-free libraries.
- **Performance**: All animations use CSS transforms and opacity for GPU acceleration.
- **Accessibility**: Reduced motion support is built-in and respects system preferences.
- **Progressive Enhancement**: All celebrations gracefully degrade if components fail to load.
