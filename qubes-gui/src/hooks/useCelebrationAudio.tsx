import { useCallback, useRef } from 'react';
import { useCelebration } from '../contexts/CelebrationContext';

/**
 * Celebration sound effects using Web Audio API
 * Generates synthesized tones for celebration events - no external audio files needed
 */

let audioContext: AudioContext | null = null;

const getAudioContext = (): AudioContext | null => {
  try {
    if (!audioContext) {
      audioContext = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
    }
    return audioContext;
  } catch {
    return null;
  }
};

const playTone = (
  frequency: number,
  duration: number,
  type: OscillatorType = 'sine',
  volume: number = 0.3,
  delay: number = 0
) => {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;

    const oscillator = ctx.createOscillator();
    const gainNode = ctx.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(ctx.destination);

    oscillator.type = type;
    oscillator.frequency.setValueAtTime(frequency, ctx.currentTime + delay);

    // Smooth envelope
    gainNode.gain.setValueAtTime(0, ctx.currentTime + delay);
    gainNode.gain.linearRampToValueAtTime(volume, ctx.currentTime + delay + 0.01);
    gainNode.gain.linearRampToValueAtTime(0, ctx.currentTime + delay + duration);

    oscillator.start(ctx.currentTime + delay);
    oscillator.stop(ctx.currentTime + delay + duration);
  } catch {
    // Audio not supported or blocked
  }
};

// ============================================================================
// Celebration Sound Definitions
// ============================================================================

const CelebrationSounds = {
  /**
   * XP Gain - Quick, bright "ding" sound
   * A short, satisfying notification tone
   */
  xpGain: () => {
    playTone(880, 0.08, 'sine', 0.2);  // A5 - bright ping
    playTone(1320, 0.12, 'sine', 0.15, 0.03); // E6 - sparkle overtone
  },

  /**
   * Level Up - Ascending major arpeggio (triumphant)
   * C5 -> E5 -> G5 -> C6
   */
  levelUp: () => {
    playTone(523, 0.15, 'sine', 0.25);      // C5
    playTone(659, 0.15, 'sine', 0.25, 0.1); // E5
    playTone(784, 0.15, 'sine', 0.25, 0.2); // G5
    playTone(1047, 0.3, 'sine', 0.3, 0.3);  // C6 - hold the resolution
  },

  /**
   * Mastery - Grand fanfare for maxing out a skill
   * Full chord with shimmer effect
   */
  mastery: () => {
    // Opening chord (C major)
    playTone(523, 0.2, 'sine', 0.2);  // C5
    playTone(659, 0.2, 'sine', 0.2);  // E5
    playTone(784, 0.2, 'sine', 0.2);  // G5

    // Rising flourish
    playTone(880, 0.15, 'sine', 0.25, 0.15);  // A5
    playTone(988, 0.15, 'sine', 0.25, 0.25);  // B5

    // Final triumphant chord (C6 major)
    playTone(1047, 0.4, 'sine', 0.3, 0.35); // C6
    playTone(1319, 0.4, 'sine', 0.25, 0.35); // E6
    playTone(1568, 0.4, 'sine', 0.2, 0.35);  // G6
  },

  /**
   * Unlock - Magical "discovery" sound
   * Shimmering upward sweep with sparkle
   */
  unlock: () => {
    // Low mysterious start
    playTone(330, 0.1, 'triangle', 0.2);  // E4

    // Quick ascending sweep
    playTone(440, 0.08, 'sine', 0.2, 0.05);  // A4
    playTone(554, 0.08, 'sine', 0.2, 0.1);   // C#5
    playTone(659, 0.08, 'sine', 0.2, 0.15);  // E5

    // Sparkle finish
    playTone(880, 0.15, 'sine', 0.25, 0.2);  // A5
    playTone(1109, 0.2, 'sine', 0.2, 0.25);  // C#6
  },

  /**
   * Milestone - Achievement unlocked fanfare
   * Bold, triumphant announcement
   */
  milestone: () => {
    // Attention-grabbing start (fifth interval)
    playTone(440, 0.12, 'sine', 0.3);  // A4
    playTone(659, 0.12, 'sine', 0.3);  // E5 (fifth)

    // Brief pause then resolution
    playTone(554, 0.15, 'sine', 0.25, 0.15); // C#5
    playTone(659, 0.15, 'sine', 0.25, 0.15); // E5

    // Final resolution chord (A major)
    playTone(880, 0.35, 'sine', 0.3, 0.3);   // A5
    playTone(1109, 0.35, 'sine', 0.25, 0.3); // C#6
    playTone(1319, 0.35, 'sine', 0.2, 0.3);  // E6
  },
};

// ============================================================================
// Hook
// ============================================================================

export const useCelebrationAudio = () => {
  const { settings } = useCelebration();
  const lastPlayedRef = useRef<Record<string, number>>({});

  // Debounce to prevent sound spam (minimum 100ms between same sounds)
  const canPlay = useCallback((soundKey: string): boolean => {
    const now = Date.now();
    const lastPlayed = lastPlayedRef.current[soundKey] || 0;
    if (now - lastPlayed < 100) return false;
    lastPlayedRef.current[soundKey] = now;
    return true;
  }, []);

  const playSound = useCallback((soundKey: keyof typeof CelebrationSounds) => {
    if (!settings.enabled || !settings.sounds) return;
    if (!canPlay(soundKey)) return;

    CelebrationSounds[soundKey]();
  }, [settings.enabled, settings.sounds, canPlay]);

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
