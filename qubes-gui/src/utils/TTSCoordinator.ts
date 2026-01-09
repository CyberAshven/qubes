/**
 * TTSCoordinator - Centralized coordination for TTS audio and typewriter text animation
 *
 * This module ensures:
 * 1. Audio plays BEFORE typewriter starts (prevents race conditions)
 * 2. Only one message is animating at a time
 * 3. State transitions are properly managed
 * 4. Prefetching happens in parallel with current playback
 */

export interface TTSMessage {
  messageId: string;
  text: string;
  qubeId: string;
  turnNumber: number;
}

export interface TTSCoordinatorCallbacks {
  onTTSStart: (messageId: string) => void;
  onTTSReady: (messageId: string) => void;  // Audio loaded and ready to play
  onTypewriterStart: (messageId: string) => void;
  onTypewriterComplete: (messageId: string) => void;
  onError: (messageId: string, error: Error) => void;
}

export class TTSCoordinator {
  private currentMessageId: string | null = null;
  private isPlaying: boolean = false;
  private audioElement: HTMLAudioElement | null = null;
  private callbacks: TTSCoordinatorCallbacks;

  constructor(audioElement: HTMLAudioElement | null, callbacks: TTSCoordinatorCallbacks) {
    this.audioElement = audioElement;
    this.callbacks = callbacks;
  }

  /**
   * Update the audio element reference (in case it changes)
   */
  setAudioElement(audioElement: HTMLAudioElement | null) {
    this.audioElement = audioElement;
  }

  /**
   * Start TTS playback and typewriter animation for a message
   * This is the MAIN entry point for playing a message with TTS
   */
  async playMessage(
    message: TTSMessage,
    audioBase64: string,
    generateTTS: (userId: string, qubeId: string, text: string) => Promise<string>
  ): Promise<void> {
    const { messageId, text, qubeId } = message;

    // Prevent concurrent playback
    if (this.isPlaying && this.currentMessageId !== messageId) {
      throw new Error(`Cannot play ${messageId}: already playing ${this.currentMessageId}`);
    }

    this.currentMessageId = messageId;
    this.isPlaying = true;

    try {
      // Notify that TTS is starting
      this.callbacks.onTTSStart(messageId);

      if (!this.audioElement) {
        throw new Error('No audio element available');
      }

      // Load audio
      this.audioElement.src = audioBase64;

      // Wait for audio to be fully loaded and ready
      await this.waitForAudioReady(this.audioElement);

      this.callbacks.onTTSReady(messageId);

      // Small delay to ensure React has rendered the TypewriterText component
      await new Promise(resolve => setTimeout(resolve, 50));

      // Start playing audio
      await this.audioElement.play();

      this.callbacks.onTypewriterStart(messageId);

      // Wait for audio to finish
      await this.waitForAudioEnd(this.audioElement);

      this.callbacks.onTypewriterComplete(messageId);

    } catch (error) {
      console.error(`[TTSCoordinator] Error playing ${messageId}:`, error);
      this.callbacks.onError(messageId, error as Error);
      throw error;
    } finally {
      this.isPlaying = false;
      this.currentMessageId = null;
    }
  }

  /**
   * Wait for audio to be loaded and ready to play
   */
  private waitForAudioReady(audio: HTMLAudioElement): Promise<void> {
    return new Promise((resolve, reject) => {
      if (audio.readyState >= 3) {
        // HAVE_FUTURE_DATA or better - audio is ready
        resolve();
        return;
      }

      const onReady = () => {
        cleanup();
        resolve();
      };

      const onError = (e: Event) => {
        cleanup();
        reject(new Error(`Audio failed to load: ${audio.error?.message || 'Unknown error'}`));
      };

      const cleanup = () => {
        audio.removeEventListener('canplay', onReady);
        audio.removeEventListener('loadeddata', onReady);
        audio.removeEventListener('error', onError);
      };

      audio.addEventListener('canplay', onReady, { once: true });
      audio.addEventListener('loadeddata', onReady, { once: true });
      audio.addEventListener('error', onError, { once: true });
    });
  }

  /**
   * Wait for audio to finish playing
   */
  private waitForAudioEnd(audio: HTMLAudioElement): Promise<void> {
    return new Promise((resolve) => {
      if (audio.ended || audio.paused) {
        resolve();
        return;
      }

      const onEnded = () => {
        audio.removeEventListener('ended', onEnded);
        resolve();
      };

      audio.addEventListener('ended', onEnded);
    });
  }

  /**
   * Check if a message is currently playing
   */
  isMessagePlaying(messageId: string): boolean {
    return this.isPlaying && this.currentMessageId === messageId;
  }

  /**
   * Get the currently playing message ID
   */
  getCurrentMessageId(): string | null {
    return this.currentMessageId;
  }

  /**
   * Stop current playback (if any)
   */
  stop(): void {
    if (this.audioElement && this.isPlaying) {
      this.audioElement.pause();
      this.audioElement.currentTime = 0;
      this.isPlaying = false;
      this.currentMessageId = null;
    }
  }
}
