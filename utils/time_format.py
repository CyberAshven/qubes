"""
Time Formatting Utilities

Consistent timestamp formatting across the application.
All user-facing timestamps use 12-hour US Eastern time.
"""

from datetime import datetime
from typing import Optional

try:
    from zoneinfo import ZoneInfo
    EASTERN_TZ = ZoneInfo('America/New_York')
except Exception:
    # Fallback for Python < 3.9, missing tzdata, or PyInstaller bundle issues
    # zoneinfo can raise ZoneInfoNotFoundError (subclass of KeyError), or other errors
    try:
        import pytz
        EASTERN_TZ = pytz.timezone('America/New_York')
    except Exception:
        # No timezone support at all - use None and fall back to local time
        EASTERN_TZ = None


def format_timestamp(
    timestamp: Optional[int],
    include_seconds: bool = False,
    short_date: bool = False
) -> str:
    """
    Format Unix timestamp to US Eastern 12-hour format

    Args:
        timestamp: Unix timestamp (seconds since epoch)
        include_seconds: Include seconds in output (default: False)
        short_date: Use short date format like "Oct 5, 2025" (default: False)

    Returns:
        Formatted timestamp string
        Examples:
            - "Thursday, October 5, 2025 2:12am"
            - "Thursday, Oct 5, 2025 2:12:30am" (with seconds)
            - "Unknown" (if timestamp is None)
    """
    if not timestamp:
        return "Unknown"

    try:
        # Convert to Eastern time
        dt = datetime.fromtimestamp(timestamp, tz=EASTERN_TZ)

        # Build format string
        if short_date:
            date_format = "%A, %b %d, %Y"  # Thursday, Oct 5, 2025
        else:
            date_format = "%A, %B %d, %Y"  # Thursday, October 5, 2025

        # Windows doesn't support %-I, so we need to manually strip leading zero
        hour = dt.strftime("%I").lstrip('0') or '12'  # Remove leading zero, default to 12 if empty
        minute = dt.strftime("%M")
        am_pm = dt.strftime("%p").lower()

        if include_seconds:
            second = dt.strftime("%S")
            time_str = f"{hour}:{minute}:{second}{am_pm}"
        else:
            time_str = f"{hour}:{minute}{am_pm}"

        date_str = dt.strftime(date_format)
        formatted = f"{date_str} {time_str}"

        return formatted

    except Exception as e:
        # Fallback without timezone
        try:
            dt = datetime.fromtimestamp(timestamp)
            if short_date:
                date_format = "%A, %b %d, %Y"
            else:
                date_format = "%A, %B %d, %Y"

            hour = dt.strftime("%I").lstrip('0') or '12'
            minute = dt.strftime("%M")
            am_pm = dt.strftime("%p").lower()

            if include_seconds:
                second = dt.strftime("%S")
                time_str = f"{hour}:{minute}:{second}{am_pm}"
            else:
                time_str = f"{hour}:{minute}{am_pm}"

            date_str = dt.strftime(date_format)
            formatted = f"{date_str} {time_str} (local time)"
            return formatted
        except Exception:
            return str(timestamp)


def format_timestamp_short(timestamp: Optional[int]) -> str:
    """
    Format timestamp in short format: "Oct 5, 2025 2:12am"

    Args:
        timestamp: Unix timestamp

    Returns:
        Short formatted timestamp
    """
    return format_timestamp(timestamp, short_date=True)


def format_timestamp_with_seconds(timestamp: Optional[int]) -> str:
    """
    Format timestamp with seconds: "October 5, 2025 2:12:30am"

    Args:
        timestamp: Unix timestamp

    Returns:
        Formatted timestamp with seconds
    """
    return format_timestamp(timestamp, include_seconds=True)


def get_current_timestamp_formatted() -> str:
    """
    Get current time in formatted Eastern time

    Returns:
        Current timestamp formatted (e.g., "October 5, 2025 2:12am")
    """
    now = int(datetime.now().timestamp())
    return format_timestamp(now)
