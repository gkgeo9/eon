#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Notification system for batch processing alerts.

Supports Discord webhooks for real-time notifications of batch events:
- Batch completed
- Batch failed
- All API keys exhausted
- System health warnings

Discord webhooks are simple HTTP POST requests, making them fast and
reliable without requiring authentication complexity.
"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, Dict, Any

# Load .env file before reading environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, rely on system environment

from fintel.core.logging import get_logger


class NotificationService:
    """
    Send notifications via Discord webhooks.

    Notifications are optional - if no webhook URL is configured,
    notification calls silently succeed without sending anything.

    Environment variables:
        FINTEL_DISCORD_WEBHOOK_URL: Discord webhook URL for notifications

    Usage:
        notifier = NotificationService()

        # Send notification
        notifier.send_batch_completed("batch-123", 100, 5)
        notifier.send_batch_failed("batch-123", "Database error")
        notifier.send_warning("Low disk space: 2GB free")
    """

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize notification service.

        Args:
            webhook_url: Discord webhook URL (or use FINTEL_DISCORD_WEBHOOK_URL env)
        """
        self.logger = get_logger(f"{__name__}.NotificationService")

        # Get webhook URL from parameter or environment
        self.webhook_url = webhook_url or os.environ.get("FINTEL_DISCORD_WEBHOOK_URL")

        if self.webhook_url:
            self.logger.info("NotificationService initialized with Discord webhook")
        else:
            self.logger.debug(
                "NotificationService initialized without webhook URL. "
                "Set FINTEL_DISCORD_WEBHOOK_URL to enable notifications."
            )

    def is_enabled(self) -> bool:
        """Check if notifications are enabled."""
        return bool(self.webhook_url)

    def _send_discord(
        self,
        content: str,
        embeds: Optional[list] = None,
        username: str = "Fintel Bot"
    ) -> bool:
        """
        Send a message to Discord webhook.

        Args:
            content: Message content
            embeds: Optional list of embed objects
            username: Bot username to display

        Returns:
            True if sent successfully
        """
        if not self.webhook_url:
            return True  # Silently succeed if not configured

        payload = {
            "username": username,
            "content": content,
        }

        if embeds:
            payload["embeds"] = embeds

        try:
            data = json.dumps(payload).encode('utf-8')
            request = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Fintel-Notification/1.0'
                }
            )

            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status in (200, 204):
                    self.logger.debug("Discord notification sent successfully")
                    return True
                else:
                    self.logger.warning(f"Discord returned status {response.status}")
                    return False

        except urllib.error.HTTPError as e:
            self.logger.error(f"Discord webhook HTTP error: {e.code} {e.reason}")
            return False
        except urllib.error.URLError as e:
            self.logger.error(f"Discord webhook URL error: {e.reason}")
            return False
        except Exception as e:
            self.logger.error(f"Discord notification failed: {e}")
            return False

    def send_batch_completed(
        self,
        batch_id: str,
        completed: int,
        failed: int,
        duration_hours: Optional[float] = None
    ) -> bool:
        """
        Send notification when batch completes.

        Args:
            batch_id: Batch ID
            completed: Number of completed items
            failed: Number of failed items
            duration_hours: How long the batch took

        Returns:
            True if sent successfully
        """
        duration_str = f" in {duration_hours:.1f} hours" if duration_hours else ""

        embed = {
            "title": "✅ Batch Completed",
            "color": 0x00FF00,  # Green
            "fields": [
                {"name": "Batch ID", "value": batch_id[:8], "inline": True},
                {"name": "Completed", "value": str(completed), "inline": True},
                {"name": "Failed", "value": str(failed), "inline": True},
            ],
            "footer": {"text": f"Fintel{duration_str}"},
            "timestamp": datetime.utcnow().isoformat()
        }

        return self._send_discord(
            content=f"Batch `{batch_id[:8]}` completed: {completed} success, {failed} failed",
            embeds=[embed]
        )

    def send_batch_progress(
        self,
        batch_id: str,
        completed: int,
        total: int,
        failed: int,
        skipped: int = 0,
        estimated_completion: Optional[str] = None,
    ) -> bool:
        """
        Send notification for batch progress milestone.

        Args:
            batch_id: Batch ID
            completed: Completed items
            total: Total items
            failed: Failed items
            skipped: Skipped items
            estimated_completion: ISO timestamp of estimated completion

        Returns:
            True if sent successfully
        """
        pct = round((completed / total) * 100, 1) if total > 0 else 0
        remaining = total - completed - failed - skipped

        # Build a text progress bar
        bar_length = 20
        filled = int(bar_length * completed / max(total, 1))
        bar = "\u2588" * filled + "\u2591" * (bar_length - filled)

        eta_str = ""
        if estimated_completion:
            try:
                eta = datetime.fromisoformat(estimated_completion)
                eta_str = eta.strftime("%Y-%m-%d %H:%M UTC")
            except Exception:
                eta_str = "N/A"

        fields = [
            {"name": "Progress", "value": f"`{bar}` {pct}%", "inline": False},
            {"name": "Completed", "value": str(completed), "inline": True},
            {"name": "Remaining", "value": str(remaining), "inline": True},
            {"name": "Failed", "value": str(failed), "inline": True},
        ]
        if eta_str:
            fields.append({"name": "ETA", "value": eta_str, "inline": True})

        embed = {
            "title": f"\U0001F4CA Batch Progress — {pct}%",
            "color": 0x3498DB,  # Blue
            "fields": fields,
            "footer": {"text": f"Fintel | Batch {batch_id[:8]}"},
            "timestamp": datetime.utcnow().isoformat(),
        }

        return self._send_discord(
            content=f"Batch `{batch_id[:8]}` progress: {completed}/{total} ({pct}%)",
            embeds=[embed],
        )

    def send_batch_failed(self, batch_id: str, error: str) -> bool:
        """
        Send notification when batch fails.

        Args:
            batch_id: Batch ID
            error: Error message

        Returns:
            True if sent successfully
        """
        # Truncate error for display
        error_display = error[:200] + "..." if len(error) > 200 else error

        embed = {
            "title": "❌ Batch Failed",
            "color": 0xFF0000,  # Red
            "fields": [
                {"name": "Batch ID", "value": batch_id[:8], "inline": True},
                {"name": "Error", "value": error_display, "inline": False},
            ],
            "footer": {"text": "Fintel - Manual intervention may be required"},
            "timestamp": datetime.utcnow().isoformat()
        }

        return self._send_discord(
            content=f"⚠️ Batch `{batch_id[:8]}` failed!",
            embeds=[embed]
        )

    def send_keys_exhausted(self, keys_count: int, next_reset: str) -> bool:
        """
        Send notification when all API keys are exhausted.

        Args:
            keys_count: Number of API keys
            next_reset: Expected reset time

        Returns:
            True if sent successfully
        """
        embed = {
            "title": "⏸️ API Keys Exhausted",
            "color": 0xFFA500,  # Orange
            "description": "All API keys have reached their daily limit. Processing will resume after midnight PST.",
            "fields": [
                {"name": "Keys", "value": str(keys_count), "inline": True},
                {"name": "Next Reset", "value": next_reset, "inline": True},
            ],
            "footer": {"text": "Fintel"},
            "timestamp": datetime.utcnow().isoformat()
        }

        return self._send_discord(
            content="All API keys exhausted - waiting for midnight reset",
            embeds=[embed]
        )

    def send_warning(self, message: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send a warning notification.

        Args:
            message: Warning message
            details: Optional details dict

        Returns:
            True if sent successfully
        """
        fields = []
        if details:
            for key, value in details.items():
                fields.append({"name": key, "value": str(value), "inline": True})

        embed = {
            "title": "⚠️ Warning",
            "color": 0xFFFF00,  # Yellow
            "description": message,
            "fields": fields,
            "footer": {"text": "Fintel"},
            "timestamp": datetime.utcnow().isoformat()
        }

        return self._send_discord(content=f"Warning: {message}", embeds=[embed])

    def send_info(self, message: str) -> bool:
        """
        Send an informational notification.

        Args:
            message: Info message

        Returns:
            True if sent successfully
        """
        return self._send_discord(content=f"ℹ️ {message}")


# Convenience function for quick notifications
def notify(message: str) -> bool:
    """
    Send a quick notification.

    Args:
        message: Message to send

    Returns:
        True if sent successfully
    """
    service = NotificationService()
    return service.send_info(message)


def notify_batch_completed(batch_id: str, completed: int, failed: int) -> bool:
    """Send batch completed notification."""
    service = NotificationService()
    return service.send_batch_completed(batch_id, completed, failed)


def notify_batch_failed(batch_id: str, error: str) -> bool:
    """Send batch failed notification."""
    service = NotificationService()
    return service.send_batch_failed(batch_id, error)
