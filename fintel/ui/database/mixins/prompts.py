#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Custom prompts database operations mixin.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any


class CustomPromptsMixin:
    """Mixin for custom prompts CRUD operations."""

    def save_prompt(
        self,
        name: str,
        description: str,
        template: str,
        analysis_type: str
    ) -> int:
        """
        Save custom prompt to database.

        Args:
            name: Prompt name (unique)
            description: Prompt description
            template: Prompt template with placeholders
            analysis_type: Analysis type this prompt is for

        Returns:
            Prompt ID

        Raises:
            sqlite3.IntegrityError: If name already exists
        """
        query = """
            INSERT INTO custom_prompts (name, description, prompt_template, analysis_type)
            VALUES (?, ?, ?, ?)
        """
        return self._execute_with_retry(query, (name, description, template, analysis_type))

    def get_prompts_by_type(self, analysis_type: str) -> List[Dict[str, Any]]:
        """Get all active prompts for an analysis type."""
        query = """
            SELECT id, name, description, prompt_template, created_at
            FROM custom_prompts
            WHERE analysis_type = ? AND is_active = 1
            ORDER BY created_at DESC
        """
        rows = self._execute_with_retry(query, (analysis_type,), fetch_all=True)

        prompts = []
        for row in rows:
            prompts.append({
                'id': row['id'],
                'name': row['name'],
                'description': row['description'],
                'template': row['prompt_template'],
                'created_at': row['created_at']
            })
        return prompts

    def get_prompt_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get prompt by name."""
        query = "SELECT * FROM custom_prompts WHERE name = ? AND is_active = 1"
        row = self._execute_with_retry(query, (name,), fetch_one=True)
        return row if row else None

    def update_prompt(self, prompt_id: int, **fields) -> None:
        """Update prompt fields."""
        allowed_fields = ['name', 'description', 'prompt_template', 'analysis_type']
        updates = []
        params = []

        for field, value in fields.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                params.append(value)

        if updates:
            updates.append("updated_at = ?")
            params.append(datetime.utcnow().isoformat())
            params.append(prompt_id)

            query = f"UPDATE custom_prompts SET {', '.join(updates)} WHERE id = ?"
            self._execute_with_retry(query, tuple(params))

    def delete_prompt(self, prompt_id: int) -> None:
        """Soft delete a prompt (set is_active = 0)."""
        query = "UPDATE custom_prompts SET is_active = 0 WHERE id = ?"
        self._execute_with_retry(query, (prompt_id,))
