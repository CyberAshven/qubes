import React, { useState, useEffect, useRef } from 'react';
import { useAudio } from '../../contexts/AudioContext';

interface TypewriterTextProps {
  text: string;
  audioElement: HTMLAudioElement | null;
  onComplete?: () => void;
  onTextUpdate?: () => void;
}

export const TypewriterText: React.FC<TypewriterTextProps> = ({ text, audioElement, onComplete, onTextUpdate }) => {
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
      // If no audio, show all text immediately
      setDisplayedText(text);
      onCompleteRef.current?.();
      return;
    }

    let animationFrame: number;
    let isComponentVisible = true;

    // Track cumulative progress across chunks
    // Each chunk handles a portion of the text
    let lastKnownDuration = 0;
    let charsPerSecondThisChunk = 0;

    // Calculate how many chars this chunk should cover
    const getChunkTextRange = () => {
      if (totalChunks <= 1) {
        return { start: 0, end: text.length };
      }
      // Divide text evenly among chunks
      const charsPerChunk = Math.ceil(text.length / totalChunks);
      const start = (currentChunk - 1) * charsPerChunk;
      const end = Math.min(currentChunk * charsPerChunk, text.length);
      return { start, end };
    };

    const updateText = () => {
      // If component became hidden, force complete immediately
      if (!isComponentVisible) {
        setDisplayedText(text);
        onCompleteRef.current?.();
        return;
      }

      // Wait for valid duration
      if (!audioElement.duration || audioElement.duration === 0 || !isFinite(audioElement.duration)) {
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
      // Add a tiny buffer (50ms worth) to stay slightly ahead for smoother feel
      const bufferChars = Math.ceil(charsPerSecondThisChunk * 0.05);
      const charsFromTime = Math.floor(audioElement.currentTime * charsPerSecondThisChunk);
      let charsInThisChunk = Math.min(chunkTextLength, charsFromTime + bufferChars);

      // CRITICAL: Never show 100% of this chunk's text until audio actually ends
      // Browser-reported duration can be inaccurate, causing typewriter to "finish"
      // before the TTS voice actually stops speaking. Cap at 98% until ended.
      if (!audioElement.ended && charsInThisChunk >= chunkTextLength) {
        charsInThisChunk = Math.floor(chunkTextLength * 0.98);
      }

      // Total chars to show = previous chunks + current chunk progress
      const totalCharsToShow = Math.min(text.length, start + charsInThisChunk);

      const newText = text.slice(0, Math.max(1, totalCharsToShow));
      setDisplayedText(newText);
      onTextUpdateRef.current?.(); // Notify parent to scroll

      // Continue updating until audio ends
      if (!audioElement.ended && !audioElement.paused) {
        // Audio still playing - continue animation
        animationFrame = requestAnimationFrame(updateText);
      } else if (audioElement.ended) {
        if (isLastChunk) {
          // Last chunk ended - NOW show all text and mark complete
          setDisplayedText(text);
          onCompleteRef.current?.();
        } else {
          // More chunks coming - show up to end of current chunk and keep animating
          // The next chunk will start playing automatically
          setDisplayedText(text.slice(0, end));
          animationFrame = requestAnimationFrame(updateText);
        }
      } else {
        // Audio paused - keep updating until it resumes or ends
        animationFrame = requestAnimationFrame(updateText);
      }
    };

    const handlePlay = () => {
      // Reset rate calculation on new play (new chunk)
      charsPerSecondThisChunk = 0;
      lastKnownDuration = 0;
      animationFrame = requestAnimationFrame(updateText);
    };

    // Handle duration changes (some browsers update duration as audio loads)
    const handleDurationChange = () => {
      if (audioElement.duration && isFinite(audioElement.duration)) {
        const { start, end } = getChunkTextRange();
        const chunkTextLength = end - start;
        lastKnownDuration = audioElement.duration;
        charsPerSecondThisChunk = chunkTextLength / audioElement.duration;
      }
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

    audioElement.addEventListener('play', handlePlay);
    audioElement.addEventListener('durationchange', handleDurationChange);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Start animation if audio is NOT paused AND has enough data loaded
    if (!audioElement.paused && audioElement.readyState >= 2) {
      // Audio is actually playing with data, start animation immediately
      animationFrame = requestAnimationFrame(updateText);
    }

    return () => {
      audioElement.removeEventListener('play', handlePlay);
      audioElement.removeEventListener('durationchange', handleDurationChange);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (animationFrame) {
        cancelAnimationFrame(animationFrame);
      }
    };
  }, [text, audioElement, totalChunks, currentChunk, isLastChunk]);

  return <span className="whitespace-pre-wrap">{displayedText}</span>;
};
