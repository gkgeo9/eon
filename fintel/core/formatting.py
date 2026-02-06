#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shared formatting utilities used by both CLI and UI layers.

This module eliminates duplicate formatting logic that was previously
implemented independently in cli/batch.py and streamlit_app.py.
"""

from datetime import datetime
from typing import Optional


def format_duration(
    start: Optional[str] = None,
    end: Optional[str] = None,
    total_seconds: Optional[int] = None,
) -> str:
    """
    Format a duration in a human-readable way.

    Accepts either a start/end ISO-format timestamp pair, or an explicit
    total_seconds value.

    Args:
        start: ISO-format start timestamp (e.g. from database).
        end: ISO-format end timestamp. If omitted, ``datetime.utcnow()`` is used.
        total_seconds: Pre-computed duration in seconds (overrides start/end).

    Returns:
        Formatted string like ``"42s"``, ``"3m 12s"``, ``"2h 15m"``, or ``"N/A"``.
    """
    if total_seconds is None:
        if not start:
            return "N/A"
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            if start_dt.tzinfo:
                start_dt = start_dt.replace(tzinfo=None)

            if end:
                end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                if end_dt.tzinfo:
                    end_dt = end_dt.replace(tzinfo=None)
            else:
                end_dt = datetime.utcnow()

            total_seconds = int((end_dt - start_dt).total_seconds())
        except Exception:
            return "N/A"

    if total_seconds < 0:
        return "N/A"

    if total_seconds < 60:
        return f"{total_seconds}s"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes}m"
