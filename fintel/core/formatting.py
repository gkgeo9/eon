#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shared formatting utilities used by both CLI and UI layers.

This module eliminates duplicate formatting logic that was previously
implemented independently across multiple CLI commands and Streamlit pages.

Consolidates:
- Duration formatting (was in cli/batch.py, streamlit_app.py, page 2)
- Status display formatting (was in streamlit_app.py, pages 2, 3, 5 — all inconsistent)
"""

from datetime import datetime
from typing import Dict, Optional, Tuple


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


# ------------------------------------------------------------------
# Status display formatting
# ------------------------------------------------------------------
# Previously defined inconsistently in:
#   - streamlit_app.py (4 statuses, with colours)
#   - pages/2_Analysis_History.py (5 statuses, with emoji pairs)
#   - pages/3_Results_Viewer.py results_display_legacy.py (3 statuses)
#   - pages/5_Settings.py (4 statuses)
# This is the single source of truth for all of them.

_STATUS_MAP: Dict[str, Tuple[str, str, str]] = {
    # status_key: (emoji, display_label, hex_colour)
    "completed": ("✅", "Completed", "#28a745"),
    "running": ("🔄", "Running", "#17a2b8"),
    "pending": ("⏳", "Queued", "#ffc107"),
    "failed": ("❌", "Failed", "#dc3545"),
    "cancelled": ("🛑", "Cancelled", "#6c757d"),
    "skipped": ("⏭️", "Skipped", "#6c757d"),
    "waiting_reset": ("🕐", "Waiting Reset", "#ffc107"),
    "stopped": ("⏸️", "Stopped", "#6c757d"),
    "paused": ("⏸️", "Paused", "#6c757d"),
}

_UNKNOWN_STATUS = ("❓", "Unknown", "#6c757d")


def format_status(status: str) -> str:
    """
    Format a status string with an emoji prefix for UI display.

    Args:
        status: Raw status string from the database (e.g. ``"completed"``).

    Returns:
        Formatted string like ``"✅ Completed"``.
    """
    emoji, label, _ = _STATUS_MAP.get(status, _UNKNOWN_STATUS)
    return f"{emoji} {label}"


def get_status_emoji(status: str) -> str:
    """Return just the emoji for a given status."""
    return _STATUS_MAP.get(status, _UNKNOWN_STATUS)[0]


def get_status_colour(status: str) -> str:
    """Return the hex colour for a given status (useful for Streamlit styling)."""
    return _STATUS_MAP.get(status, _UNKNOWN_STATUS)[2]
