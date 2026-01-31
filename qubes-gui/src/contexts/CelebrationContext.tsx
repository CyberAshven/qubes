import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';
import { listen } from '@tauri-apps/api/event';

// ============================================================================
// Types
// ============================================================================

export interface XPGainEvent {
  id: string;
  qubeId: string;
  skillId: string;
  skillName: string;
  skillIcon: string;
  categoryColor: string;
  nodeType: 'sun' | 'planet' | 'moon';
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
  maxedOut: boolean; // True when level hits 100
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

  // Event triggers (called by skill system or backend events)
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

// ============================================================================
// Default Settings
// ============================================================================

const DEFAULT_SETTINGS: CelebrationSettings = {
  enabled: true,
  xpToasts: true,
  levelUpModals: true,
  unlockAnimations: true,
  confetti: true,
  sounds: true,
  reducedMotion: false,
};

// ============================================================================
// Context
// ============================================================================

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

    // Listen for changes
    const handleChange = (e: MediaQueryListEvent) => {
      setSettings(prev => ({ ...prev, reducedMotion: e.matches }));
    };
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
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

  // ============================================================================
  // Event Triggers
  // ============================================================================

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

  // ============================================================================
  // Event Dismissal
  // ============================================================================

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

  // ============================================================================
  // Backend Event Listeners
  // ============================================================================

  useEffect(() => {
    // Listen for chain-state-event and filter for skill-related events
    // This matches the event format emitted by the Rust event watcher
    const unlistenChainState = listen<{
      type: string;
      qube_id: string;
      event_type: string;
      payload: Record<string, unknown>;
      timestamp: number;
      source: string;
    }>('chain-state-event', (event) => {
      const { qube_id, event_type, payload } = event.payload;

      // Handle XP gained events
      if (event_type === 'xp_gained') {
        const data = payload as {
          skill_id: string;
          skill_name: string;
          skill_icon: string;
          category_color: string;
          node_type: 'sun' | 'planet' | 'moon';
          xp_amount: number;
          new_xp: number;
          max_xp: number;
          previous_level: number;
          new_level: number;
          leveled_up: boolean;
          maxed_out: boolean;
          tool_unlocked?: string;
        };

        triggerXPGain({
          qubeId: qube_id,
          skillId: data.skill_id,
          skillName: data.skill_name,
          skillIcon: data.skill_icon,
          categoryColor: data.category_color,
          nodeType: data.node_type,
          xpAmount: data.xp_amount,
          newXP: data.new_xp,
          maxXP: data.max_xp,
          previousLevel: data.previous_level,
          newLevel: data.new_level,
        });

        // Check for level up
        if (data.leveled_up) {
          triggerLevelUp({
            qubeId: qube_id,
            skillId: data.skill_id,
            skillName: data.skill_name,
            skillIcon: data.skill_icon,
            categoryColor: data.category_color,
            nodeType: data.node_type,
            newLevel: data.new_level,
            maxedOut: data.maxed_out,
          });
        }
      }

      // Handle skill unlocked events (when a skill is maxed and unlocks a tool)
      if (event_type === 'skill_unlocked') {
        const data = payload as {
          skill_id: string;
          skill_name: string;
          skill_icon: string;
          category_color: string;
          node_type: 'sun' | 'planet' | 'moon';
          tool_unlocked?: string;
        };

        triggerSkillUnlock({
          qubeId: qube_id,
          skillId: data.skill_id,
          skillName: data.skill_name,
          skillIcon: data.skill_icon,
          categoryColor: data.category_color,
          nodeType: data.node_type,
        });
      }
    });

    // Cleanup listener
    return () => {
      unlistenChainState.then(fn => fn());
    };
  }, [triggerXPGain, triggerLevelUp, triggerSkillUnlock]);

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
