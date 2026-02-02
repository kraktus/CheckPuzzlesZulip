from datetime import datetime, timezone


def utc_now():
    """Return the current time in UTC."""
    return datetime.now(timezone.utc)
