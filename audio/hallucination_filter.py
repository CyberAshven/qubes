"""
Hallucination Filter

Detects and filters STT hallucinations (false transcriptions).
From docs/27_Audio_TTS_STT_Integration.md Section 7.3
"""

from typing import List

from utils.logging import get_logger

logger = get_logger(__name__)


class HallucinationFilter:
    """Detect likely STT hallucinations"""

    # Common hallucination phrases (often appears in Whisper output)
    COMMON_HALLUCINATIONS: List[str] = [
        "thank you for watching",
        "please subscribe",
        "like and subscribe",
        "see you next time",
        "goodbye everyone",
        "thanks for listening",
        "that's all for today",
        "visit our website",
        "follow us on",
        "don't forget to",
        "stay tuned",
        "coming up next",
    ]

    # Minimum confidence threshold
    MIN_CONFIDENCE = 0.80

    # Minimum text length (chars)
    MIN_TEXT_LENGTH = 3

    def __init__(self):
        logger.debug("hallucination_filter_initialized")

    def is_likely_hallucination(self, text: str, confidence: float = 1.0) -> bool:
        """
        Detect likely hallucinations

        Args:
            text: Transcribed text
            confidence: Confidence score (0.0 - 1.0)

        Returns:
            True if likely hallucination, False otherwise
        """
        text_lower = text.lower().strip()

        logger.debug(
            "checking_hallucination",
            text_length=len(text_lower),
            confidence=confidence
        )

        # Low confidence
        if confidence < self.MIN_CONFIDENCE:
            logger.info(
                "hallucination_detected",
                reason="low_confidence",
                confidence=confidence,
                text=text[:50]
            )
            return True

        # Known hallucination patterns
        for phrase in self.COMMON_HALLUCINATIONS:
            if phrase in text_lower:
                logger.info(
                    "hallucination_detected",
                    reason="known_phrase",
                    phrase=phrase,
                    text=text[:50]
                )
                return True

        # Empty or very short
        if len(text_lower) < self.MIN_TEXT_LENGTH:
            logger.info(
                "hallucination_detected",
                reason="too_short",
                length=len(text_lower),
                text=text
            )
            return True

        # Not a hallucination
        logger.debug("hallucination_check_passed", text=text[:50])
        return False

    def filter_text(self, text: str, confidence: float = 1.0) -> str | None:
        """
        Filter text, return None if hallucination

        Args:
            text: Transcribed text
            confidence: Confidence score

        Returns:
            Original text if valid, None if hallucination
        """
        if self.is_likely_hallucination(text, confidence):
            return None
        return text
