"""
Audio Rate Limiter

Tracks usage and enforces quota limits for TTS/STT API calls.
From docs/27_Audio_TTS_STT_Integration.md Section 9.2
"""

from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict

from utils.logging import get_logger

logger = get_logger(__name__)


class AudioRateLimiter:
    """Rate limiter and quota tracker for audio APIs"""

    def __init__(self):
        """Initialize rate limiter"""
        self.tts_usage: Dict[str, int] = defaultdict(int)  # user_id → chars this month
        self.stt_usage: Dict[str, int] = defaultdict(int)  # user_id → seconds this month
        self.last_reset = datetime.now()

        logger.info("audio_rate_limiter_initialized")

    def reset_monthly(self):
        """Reset usage counters (called by cron job)"""
        if datetime.now() - self.last_reset > timedelta(days=30):
            logger.info(
                "resetting_monthly_usage",
                tts_users=len(self.tts_usage),
                stt_users=len(self.stt_usage)
            )

            self.tts_usage.clear()
            self.stt_usage.clear()
            self.last_reset = datetime.now()

    def check_tts_quota(
        self,
        user_id: str,
        text: str,
        provider: str,
        premium: bool = False
    ) -> bool:
        """
        Check if user has TTS quota remaining

        Args:
            user_id: User identifier
            text: Text to synthesize
            provider: TTS provider (openai, elevenlabs, piper)
            premium: Whether user has premium subscription

        Returns:
            True if quota available, False if exceeded
        """
        if premium:
            logger.debug("tts_quota_check_bypassed", user_id=user_id, reason="premium")
            return True  # Unlimited for premium users

        chars = len(text)

        # ElevenLabs free tier: 30K chars/month
        if provider == "elevenlabs":
            current_usage = self.tts_usage[user_id]
            if current_usage + chars > 30_000:
                logger.warning(
                    "tts_quota_exceeded",
                    user_id=user_id,
                    provider=provider,
                    current_usage=current_usage,
                    requested_chars=chars,
                    limit=30_000
                )
                return False

            # Warn at 80%
            if current_usage + chars > 24_000 and current_usage <= 24_000:
                logger.info(
                    "tts_quota_warning",
                    user_id=user_id,
                    provider=provider,
                    usage=current_usage + chars,
                    limit=30_000,
                    percent=round(((current_usage + chars) / 30_000) * 100, 1)
                )

        # Track usage
        self.tts_usage[user_id] += chars

        logger.debug(
            "tts_quota_checked",
            user_id=user_id,
            provider=provider,
            chars=chars,
            total_usage=self.tts_usage[user_id]
        )

        return True

    def check_stt_quota(
        self,
        user_id: str,
        duration_seconds: float,
        premium: bool = False
    ) -> bool:
        """
        Check if user has STT quota remaining

        Args:
            user_id: User identifier
            duration_seconds: Audio duration in seconds
            premium: Whether user has premium subscription

        Returns:
            True if quota available, False if exceeded
        """
        if premium:
            logger.debug("stt_quota_check_bypassed", user_id=user_id, reason="premium")
            return True  # Unlimited for premium users

        # Free tier: 60 minutes/month
        current_usage = self.stt_usage[user_id]
        if current_usage + duration_seconds > 3600:  # 60 min = 3600 sec
            logger.warning(
                "stt_quota_exceeded",
                user_id=user_id,
                current_usage_minutes=round(current_usage / 60, 1),
                requested_seconds=duration_seconds,
                limit_minutes=60
            )
            return False

        # Warn at 80% (48 minutes)
        if current_usage + duration_seconds > 2880 and current_usage <= 2880:
            logger.info(
                "stt_quota_warning",
                user_id=user_id,
                usage_minutes=round((current_usage + duration_seconds) / 60, 1),
                limit_minutes=60,
                percent=round(((current_usage + duration_seconds) / 3600) * 100, 1)
            )

        # Track usage
        self.stt_usage[user_id] += duration_seconds

        logger.debug(
            "stt_quota_checked",
            user_id=user_id,
            duration_seconds=duration_seconds,
            total_usage_minutes=round(self.stt_usage[user_id] / 60, 1)
        )

        return True

    def get_usage_stats(self, user_id: str) -> Dict[str, any]:
        """
        Get usage statistics for a user

        Args:
            user_id: User identifier

        Returns:
            Dict with TTS and STT usage stats
        """
        tts_chars = self.tts_usage.get(user_id, 0)
        stt_seconds = self.stt_usage.get(user_id, 0)

        stats = {
            "user_id": user_id,
            "tts_chars_used": tts_chars,
            "tts_chars_remaining": max(0, 30_000 - tts_chars),  # ElevenLabs free tier
            "tts_percent_used": round((tts_chars / 30_000) * 100, 1) if tts_chars > 0 else 0.0,
            "stt_minutes_used": round(stt_seconds / 60, 1),
            "stt_minutes_remaining": round(max(0, 3600 - stt_seconds) / 60, 1),
            "stt_percent_used": round((stt_seconds / 3600) * 100, 1) if stt_seconds > 0 else 0.0,
            "last_reset": self.last_reset.isoformat(),
        }

        logger.debug("usage_stats_retrieved", **stats)

        return stats

    def reset_user_usage(self, user_id: str):
        """
        Reset usage for a specific user

        Args:
            user_id: User identifier
        """
        if user_id in self.tts_usage:
            del self.tts_usage[user_id]
        if user_id in self.stt_usage:
            del self.stt_usage[user_id]

        logger.info("user_usage_reset", user_id=user_id)
