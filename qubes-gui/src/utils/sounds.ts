/**
 * Chess sound effects using Web Audio API
 * Generates simple tones for game events
 */

let audioContext: AudioContext | null = null;

const getAudioContext = (): AudioContext => {
  if (!audioContext) {
    audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
  }
  return audioContext;
};

const playTone = (frequency: number, duration: number, type: OscillatorType = 'sine', volume: number = 0.3) => {
  try {
    const ctx = getAudioContext();
    const oscillator = ctx.createOscillator();
    const gainNode = ctx.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(ctx.destination);

    oscillator.type = type;
    oscillator.frequency.setValueAtTime(frequency, ctx.currentTime);

    // Envelope for smoother sound
    gainNode.gain.setValueAtTime(0, ctx.currentTime);
    gainNode.gain.linearRampToValueAtTime(volume, ctx.currentTime + 0.01);
    gainNode.gain.linearRampToValueAtTime(0, ctx.currentTime + duration);

    oscillator.start(ctx.currentTime);
    oscillator.stop(ctx.currentTime + duration);
  } catch (e) {
    // Audio not supported or blocked
    console.debug('Audio playback failed:', e);
  }
};

const playChord = (frequencies: number[], duration: number, type: OscillatorType = 'sine', volume: number = 0.2) => {
  frequencies.forEach(freq => playTone(freq, duration, type, volume / frequencies.length));
};

export const ChessSounds = {
  /**
   * Play sound for a regular piece move
   */
  move: () => {
    playTone(440, 0.1, 'sine', 0.2); // A4, short click
  },

  /**
   * Play sound for a capture
   */
  capture: () => {
    playTone(330, 0.08, 'square', 0.25); // E4, sharper attack sound
    setTimeout(() => playTone(220, 0.12, 'sine', 0.2), 50); // A3, follow-up thud
  },

  /**
   * Play sound for check
   */
  check: () => {
    playTone(880, 0.15, 'sine', 0.3); // A5, alert tone
    setTimeout(() => playTone(660, 0.1, 'sine', 0.2), 100); // E5, descending
  },

  /**
   * Play sound for checkmate (victory)
   */
  checkmate: () => {
    // Major chord arpeggio: C-E-G-C
    playTone(523, 0.2, 'sine', 0.25); // C5
    setTimeout(() => playTone(659, 0.2, 'sine', 0.25), 100); // E5
    setTimeout(() => playTone(784, 0.2, 'sine', 0.25), 200); // G5
    setTimeout(() => playTone(1047, 0.4, 'sine', 0.3), 300); // C6
  },

  /**
   * Play sound for game start
   */
  gameStart: () => {
    playTone(440, 0.1, 'sine', 0.2); // A4
    setTimeout(() => playTone(554, 0.1, 'sine', 0.2), 100); // C#5
    setTimeout(() => playTone(659, 0.15, 'sine', 0.25), 200); // E5
  },

  /**
   * Play sound for draw
   */
  draw: () => {
    playTone(440, 0.2, 'sine', 0.2); // A4
    setTimeout(() => playTone(440, 0.3, 'sine', 0.15), 250); // A4 again
  },

  /**
   * Play sound for illegal move attempt
   */
  illegal: () => {
    playTone(200, 0.15, 'square', 0.2); // Low buzz
  },

  /**
   * Play appropriate sound based on move result
   */
  playMoveSound: (isCapture: boolean, isCheck: boolean, isCheckmate: boolean, isDraw: boolean) => {
    if (isCheckmate) {
      ChessSounds.checkmate();
    } else if (isDraw) {
      ChessSounds.draw();
    } else if (isCheck) {
      ChessSounds.check();
    } else if (isCapture) {
      ChessSounds.capture();
    } else {
      ChessSounds.move();
    }
  },
};

export default ChessSounds;
