import React, { useState, useEffect, useRef } from 'react';

interface TypewriterTextProps {
  text: string;
  audioElement: HTMLAudioElement | null;
  onComplete?: () => void;
  onTextUpdate?: () => void;
}

export const TypewriterText: React.FC<TypewriterTextProps> = ({ text, audioElement, onComplete, onTextUpdate }) => {
  const [displayedText, setDisplayedText] = useState('');

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

  // Lead time: typewriter runs 1 second ahead of audio for more natural feel
  const LEAD_TIME_SECONDS = 1.0;

  useEffect(() => {
    if (!audioElement) {
      // If no audio, show all text immediately
      setDisplayedText(text);
      onCompleteRef.current?.();
      return;
    }

    let animationFrame: number;
    let isComponentVisible = true;

    const updateText = () => {
      // If component became hidden, force complete immediately
      if (!isComponentVisible) {
        setDisplayedText(text);
        onCompleteRef.current?.();
        return;
      }

      if (!audioElement.duration || audioElement.duration === 0) {
        animationFrame = requestAnimationFrame(updateText);
        return;
      }

      // Calculate progress with lead time (typewriter runs 0.5s ahead)
      const leadTimeProgress = LEAD_TIME_SECONDS / audioElement.duration;
      const audioProgress = audioElement.currentTime / audioElement.duration;
      const typewriterProgress = Math.min(1, audioProgress + leadTimeProgress);

      // Calculate characters to show based on progress
      const charsToShow = Math.floor(typewriterProgress * text.length);
      const newText = text.slice(0, Math.max(1, charsToShow));

      setDisplayedText(newText);
      onTextUpdateRef.current?.(); // Notify parent to scroll

      // Continue updating until audio ends
      // NOTE: We show all text when typewriter reaches 100% (due to lead time),
      // but we DON'T call onComplete until audio actually ends
      if (!audioElement.ended && !audioElement.paused) {
        // Audio still playing - continue animation
        animationFrame = requestAnimationFrame(updateText);
      } else if (audioElement.ended) {
        // Audio has ended - show all text and mark complete
        setDisplayedText(text);
        onCompleteRef.current?.();
      } else {
        // Audio paused - keep updating until it resumes or ends
        animationFrame = requestAnimationFrame(updateText);
      }
    };

    // DON'T bail out on error or ended state!
    // The audio element might be in a stale state from the previous playback.
    // We'll wait for the 'play' event which fires when the NEW audio starts.
    // If the audio truly never plays, the parent will handle timeout/cleanup.

    const handlePlay = () => {
      animationFrame = requestAnimationFrame(updateText);
    };

    // Handle visibility changes - force complete when hidden
    const handleVisibilityChange = () => {
      if (document.hidden) {
        isComponentVisible = false;
        if (animationFrame) {
          cancelAnimationFrame(animationFrame);
        }
        setDisplayedText(text);
        onCompleteRef.current?.();
      }
    };

    // DON'T listen to 'ended' event!
    // The audio element is shared across all messages, so the 'ended' event
    // might fire for the PREVIOUS message's audio, not this one.
    // Instead, the animation loop (updateText) will detect completion naturally
    // by checking audioElement.ended or when all text is shown.

    audioElement.addEventListener('play', handlePlay);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Start animation if audio is NOT paused AND has enough data loaded
    // This prevents starting animation on stale audio state during transitions
    // readyState >= 2 means we have current data (HAVE_CURRENT_DATA or better)
    // Note: We don't check currentTime > 0 because the component might mount right as
    // audio starts, when currentTime is still exactly 0 (race condition)
    if (!audioElement.paused && audioElement.readyState >= 2) {
      // Audio is actually playing with data, start animation immediately
      animationFrame = requestAnimationFrame(updateText);
    }
    // Otherwise wait for play event

    return () => {
      audioElement.removeEventListener('play', handlePlay);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (animationFrame) {
        cancelAnimationFrame(animationFrame);
      }
    };
  }, [text, audioElement]); // Removed onComplete and onTextUpdate from dependencies - using refs instead

  return <span className="whitespace-pre-wrap">{displayedText}</span>;
};
