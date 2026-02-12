import React, { useState, useEffect, useRef } from 'react';
import { useAudio, AudioPlaybackElement } from '../../contexts/AudioContext';

interface TypewriterTextProps {
  text: string;
  audioElement: AudioPlaybackElement | null;
  onComplete?: () => void;
  onTextUpdate?: () => void;
}

// Memoized to prevent re-renders when parent components update (e.g., ToolCallBubble expansion)
export const TypewriterText: React.FC<TypewriterTextProps> = React.memo(({ text, audioElement, onComplete, onTextUpdate }) => {
  const [displayedText, setDisplayedText] = useState('');
  const { totalChunks, currentChunk, isLastChunk } = useAudio();

  // Use refs for callbacks to avoid re-running effect when callbacks change
  const onCompleteRef = useRef(onComplete);
  const onTextUpdateRef = useRef(onTextUpdate);

  // Keep refs in sync with latest callbacks
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    onTextUpdateRef.current = onTextUpdate;
  }, [onTextUpdate]);

  useEffect(() => {
    if (!audioElement) {
      // If no audio element at all, show all text immediately
      setDisplayedText(text);
      onCompleteRef.current?.();
      return;
    }

    let animationFrame: number;
    let completed = false;
    let fallbackMode = false;
    let fallbackStartTime = 0;
    const CHARS_PER_SECOND = 40; // Fallback typing speed (natural reading pace)
    const AUDIO_WAIT_MS = 800; // Wait for audio before falling back
    const mountTime = performance.now();

    const forceComplete = () => {
      if (completed) return;
      completed = true;
      setDisplayedText(text);
      onCompleteRef.current?.();
    };

    // Safety timeout: absolute last resort if nothing else works.
    // Set to 120s - this should NEVER fire in normal operation.
    // Normal exits: audio 'ended' event, fallback animation completing, or visibility change.
    const safetyTimeout = setTimeout(() => {
      if (!completed) {
        console.warn('[TypewriterText] Safety timeout reached (120s), forcing complete');
        forceComplete();
      }
    }, 120000);

    // Track cumulative progress across chunks
    let lastKnownDuration = 0;
    let charsPerSecondThisChunk = 0;

    // Calculate how many chars this chunk should cover
    const getChunkTextRange = () => {
      if (totalChunks <= 1) {
        return { start: 0, end: text.length };
      }
      const charsPerChunk = Math.ceil(text.length / totalChunks);
      const start = (currentChunk - 1) * charsPerChunk;
      const end = Math.min(currentChunk * charsPerChunk, text.length);
      return { start, end };
    };

    const startFallbackMode = () => {
      if (fallbackMode || completed) return;
      fallbackMode = true;
      fallbackStartTime = performance.now();
      // Cancel the safety timeout - fallback mode has its own completion logic
      // (the timeout was meant for audio-sync mode getting stuck, not for fallback)
      clearTimeout(safetyTimeout);
    };

    const updateText = () => {
      if (completed) return;

      // Check if we should switch to fallback mode
      if (!fallbackMode) {
        const elapsed = performance.now() - mountTime;
        const audioNotProgressing = audioElement.currentTime < 0.1;
        const audioHasError = !!audioElement.error;
        const audioStale = audioElement.ended && audioElement.currentTime === 0;

        // Switch to fallback if:
        // 1. Audio has an error
        // 2. Audio is in a stale ended state (from previous playback, never loaded new audio)
        // 3. Audio currentTime hasn't advanced past 0.1s after the wait period
        //    (covers: audio "playing" but corrupt, audio paused, audio not loaded, etc.)
        if (audioHasError || audioStale || (elapsed > AUDIO_WAIT_MS && audioNotProgressing)) {
          startFallbackMode();
        }
      }

      // === FALLBACK MODE: Time-based typewriter ===
      if (fallbackMode) {
        const elapsed = (performance.now() - fallbackStartTime) / 1000;
        const charsToShow = Math.min(text.length, Math.floor(elapsed * CHARS_PER_SECOND));

        if (charsToShow >= text.length) {
          clearTimeout(safetyTimeout);
          setDisplayedText(text);
          completed = true;
          setTimeout(() => onCompleteRef.current?.(), 150);
          return;
        }

        setDisplayedText(text.slice(0, Math.max(1, charsToShow)));
        onTextUpdateRef.current?.();
        animationFrame = requestAnimationFrame(updateText);
        return;
      }

      // === AUDIO-SYNC MODE ===

      // Audio ended - show remaining text
      if (audioElement.ended) {
        if (isLastChunk) {
          clearTimeout(safetyTimeout);
          setDisplayedText(text);
          completed = true;
          setTimeout(() => onCompleteRef.current?.(), 150);
        } else {
          const { end } = getChunkTextRange();
          setDisplayedText(text.slice(0, end));
          animationFrame = requestAnimationFrame(updateText);
        }
        return;
      }

      // Wait for valid duration - but show at least some text while waiting
      if (!audioElement.duration || audioElement.duration === 0 || !isFinite(audioElement.duration)) {
        // Show first char while waiting for duration (better than empty)
        if (text.length > 0) {
          setDisplayedText(text.slice(0, 1));
        }
        animationFrame = requestAnimationFrame(updateText);
        return;
      }

      const { start, end } = getChunkTextRange();
      const chunkTextLength = end - start;

      // Recalculate rate if duration changed
      if (audioElement.duration !== lastKnownDuration) {
        lastKnownDuration = audioElement.duration;
        charsPerSecondThisChunk = chunkTextLength / audioElement.duration;
      }

      // Calculate characters to show for this chunk
      const bufferChars = Math.ceil(charsPerSecondThisChunk * 0.05);
      const charsFromTime = Math.floor(audioElement.currentTime * charsPerSecondThisChunk);
      let charsInThisChunk = Math.min(chunkTextLength, charsFromTime + bufferChars);

      const totalCharsToShow = Math.min(text.length, start + charsInThisChunk);
      const newText = text.slice(0, Math.max(1, totalCharsToShow));
      setDisplayedText(newText);
      onTextUpdateRef.current?.();

      // Continue animation based on audio state
      if (!audioElement.ended && !audioElement.paused) {
        animationFrame = requestAnimationFrame(updateText);
      } else if (audioElement.ended) {
        if (isLastChunk) {
          clearTimeout(safetyTimeout);
          setDisplayedText(text);
          completed = true;
          setTimeout(() => onCompleteRef.current?.(), 150);
        } else {
          setDisplayedText(text.slice(0, end));
          animationFrame = requestAnimationFrame(updateText);
        }
      } else if (audioElement.error) {
        startFallbackMode();
        animationFrame = requestAnimationFrame(updateText);
      } else {
        // Audio paused - keep polling
        animationFrame = requestAnimationFrame(updateText);
      }
    };

    const handlePlay = () => {
      if (completed) return;
      // If we were in fallback mode and audio starts, stay in fallback
      // (don't switch back mid-animation, it would be jarring)
      if (fallbackMode) return;
      charsPerSecondThisChunk = 0;
      lastKnownDuration = 0;
      animationFrame = requestAnimationFrame(updateText);
    };

    const handleEnded = () => {
      if (completed) return;
      animationFrame = requestAnimationFrame(updateText);
    };

    const handleDurationChange = () => {
      if (audioElement.duration && isFinite(audioElement.duration)) {
        const { start, end } = getChunkTextRange();
        const chunkTextLength = end - start;
        lastKnownDuration = audioElement.duration;
        charsPerSecondThisChunk = chunkTextLength / audioElement.duration;
      }
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        if (animationFrame) cancelAnimationFrame(animationFrame);
        clearTimeout(safetyTimeout);
        forceComplete();
      }
    };

    const handleError = () => {
      if (completed) return;
      startFallbackMode();
      animationFrame = requestAnimationFrame(updateText);
    };

    audioElement.addEventListener('play', handlePlay);
    audioElement.addEventListener('ended', handleEnded);
    audioElement.addEventListener('error', handleError);
    audioElement.addEventListener('durationchange', handleDurationChange);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Check current audio state and start accordingly
    if (audioElement.error) {
      startFallbackMode();
      animationFrame = requestAnimationFrame(updateText);
    } else if (audioElement.ended && audioElement.currentTime === 0) {
      startFallbackMode();
      animationFrame = requestAnimationFrame(updateText);
    } else if (audioElement.ended) {
      clearTimeout(safetyTimeout);
      forceComplete();
    } else {
      animationFrame = requestAnimationFrame(updateText);
    }

    return () => {
      audioElement.removeEventListener('play', handlePlay);
      audioElement.removeEventListener('ended', handleEnded);
      audioElement.removeEventListener('error', handleError);
      audioElement.removeEventListener('durationchange', handleDurationChange);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      clearTimeout(safetyTimeout);
      if (animationFrame) {
        cancelAnimationFrame(animationFrame);
      }
    };
  }, [text, audioElement, totalChunks, currentChunk, isLastChunk]);

  return <span className="whitespace-pre-wrap">{displayedText}</span>;
});
