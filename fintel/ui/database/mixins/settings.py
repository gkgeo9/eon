#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
User settings database operations mixin.
"""

from datetime import datetime
from typing import Any


class UserSettingsMixin:
    """Mixin for user settings CRUD operations."""

    def set_setting(self, key: str, value: str) -> None:
        """Set user setting."""
        query = """
            INSERT OR REPLACE INTO user_settings (key, value, updated_at)
            VALUES (?, ?, ?)
        """
        self._execute_with_retry(query, (key, value, datetime.utcnow().isoformat()))

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a user setting value.

        Args:
            key: Setting key
            default: Default value if not found

        Returns:
            Setting value or default
        """
        query = "SELECT value FROM user_settings WHERE key = ?"
        row = self._execute_with_retry(query, (key,), fetch_one=True)
        return row['value'] if row else default

    def save_setting(self, key: str, value: str) -> None:
        """
        Save a user setting.

        Args:
            key: Setting key
            value: Setting value
        """
        query = """
            INSERT INTO user_settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
        """
        self._execute_with_retry(query, (key, str(value)))
