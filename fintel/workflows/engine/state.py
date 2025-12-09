#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WorkflowState - Tracks workflow execution progress and enables resume capability.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
import json

from .data_container import DataContainer


@dataclass
class WorkflowState:
    """
    Tracks workflow execution state for progress monitoring and resume capability.

    The state is persisted to the database after each step, allowing
    workflows to be resumed if they fail mid-execution.
    """

    workflow_run_id: str
    workflow_id: int

    # Progress tracking
    current_step_index: int = 0
    total_steps: int = 0
    status: Literal["pending", "running", "completed", "failed", "paused"] = "pending"

    # Data passing between steps
    step_outputs: Dict[str, DataContainer] = field(default_factory=dict)

    # Error tracking
    errors: List[Dict[str, Any]] = field(default_factory=list)

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Resume capability
    last_successful_step: Optional[str] = None

    def save(self, db):
        """
        Persist state to database.

        Args:
            db: DatabaseRepository instance
        """
        from fintel.core import get_logger
        logger = get_logger(__name__)

        # Update or insert workflow run
        try:
            # Check if run exists
            existing = db._execute_with_retry(
                "SELECT id FROM workflow_runs WHERE id = ?",
                (self.workflow_run_id,)
            ).fetchone()

            if existing:
                # Update existing run
                query = """
                    UPDATE workflow_runs
                    SET status = ?,
                        current_step_index = ?,
                        total_steps = ?,
                        started_at = ?,
                        completed_at = ?,
                        last_successful_step = ?,
                        errors_json = ?
                    WHERE id = ?
                """
                db._execute_with_retry(query, (
                    self.status,
                    self.current_step_index,
                    self.total_steps,
                    self.started_at.isoformat() if self.started_at else None,
                    self.completed_at.isoformat() if self.completed_at else None,
                    self.last_successful_step,
                    json.dumps(self.errors),
                    self.workflow_run_id
                ))
            else:
                # Insert new run
                query = """
                    INSERT INTO workflow_runs (
                        id, workflow_id, status, current_step_index, total_steps,
                        started_at, completed_at, last_successful_step, errors_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                db._execute_with_retry(query, (
                    self.workflow_run_id,
                    self.workflow_id,
                    self.status,
                    self.current_step_index,
                    self.total_steps,
                    self.started_at.isoformat() if self.started_at else None,
                    self.completed_at.isoformat() if self.completed_at else None,
                    self.last_successful_step,
                    json.dumps(self.errors)
                ))

            logger.info(f"Saved workflow state: {self.workflow_run_id} (status: {self.status})")

        except Exception as e:
            logger.error(f"Failed to save workflow state: {e}", exc_info=True)
            raise

    def save_step_output(self, step_id: str, output: DataContainer, db):
        """
        Save step output to database for resume capability.

        Args:
            step_id: Step identifier
            output: DataContainer from step execution
            db: DatabaseRepository instance
        """
        from fintel.core import get_logger
        logger = get_logger(__name__)

        try:
            # Store in memory
            self.step_outputs[step_id] = output

            # Serialize to JSON
            output_json = output.to_json()

            # Save to database (INSERT OR REPLACE for idempotency)
            query = """
                INSERT OR REPLACE INTO workflow_step_outputs (
                    workflow_run_id, step_id, output_json, created_at
                ) VALUES (?, ?, ?, ?)
            """
            db._execute_with_retry(query, (
                self.workflow_run_id,
                step_id,
                output_json,
                datetime.now().isoformat()
            ))

            logger.info(f"Saved step output: {step_id} ({output.total_items} items)")

        except Exception as e:
            logger.error(f"Failed to save step output: {e}", exc_info=True)
            raise

    def load_step_output(self, step_id: str, db) -> Optional[DataContainer]:
        """
        Load step output from database.

        Args:
            step_id: Step identifier
            db: DatabaseRepository instance

        Returns:
            DataContainer if found, None otherwise
        """
        from fintel.core import get_logger
        logger = get_logger(__name__)

        try:
            # Check memory first
            if step_id in self.step_outputs:
                return self.step_outputs[step_id]

            # Load from database
            query = """
                SELECT output_json
                FROM workflow_step_outputs
                WHERE workflow_run_id = ? AND step_id = ?
            """
            cursor = db._execute_with_retry(query, (self.workflow_run_id, step_id))
            row = cursor.fetchone()

            if row:
                output_json = row[0]
                container = DataContainer.from_json(output_json)
                self.step_outputs[step_id] = container
                logger.info(f"Loaded step output: {step_id}")
                return container

            return None

        except Exception as e:
            logger.error(f"Failed to load step output: {e}", exc_info=True)
            return None

    def log_step(self, step_id: str, level: str, message: str, db):
        """
        Log a step execution message.

        Args:
            step_id: Step identifier
            level: Log level (INFO, WARNING, ERROR)
            message: Log message
            db: DatabaseRepository instance
        """
        try:
            query = """
                INSERT INTO workflow_step_logs (
                    workflow_run_id, step_id, log_level, message, created_at
                ) VALUES (?, ?, ?, ?, ?)
            """
            db._execute_with_retry(query, (
                self.workflow_run_id,
                step_id,
                level,
                message,
                datetime.now().isoformat()
            ))
        except Exception as e:
            from fintel.core import get_logger
            logger = get_logger(__name__)
            logger.error(f"Failed to log step message: {e}")

    def add_error(self, step_id: str, error_message: str, error_details: Optional[Dict] = None):
        """Add an error to the state."""
        self.errors.append({
            'step_id': step_id,
            'message': error_message,
            'details': error_details or {},
            'timestamp': datetime.now().isoformat()
        })

    @classmethod
    def load(cls, workflow_run_id: str, db) -> Optional['WorkflowState']:
        """
        Load workflow state from database.

        Args:
            workflow_run_id: Workflow run UUID
            db: DatabaseRepository instance

        Returns:
            WorkflowState if found, None otherwise
        """
        from fintel.core import get_logger
        logger = get_logger(__name__)

        try:
            query = """
                SELECT
                    id, workflow_id, status, current_step_index, total_steps,
                    started_at, completed_at, last_successful_step, errors_json
                FROM workflow_runs
                WHERE id = ?
            """
            cursor = db._execute_with_retry(query, (workflow_run_id,))
            row = cursor.fetchone()

            if not row:
                logger.warning(f"Workflow run not found: {workflow_run_id}")
                return None

            # Parse row
            state = cls(
                workflow_run_id=row[0],
                workflow_id=row[1],
                status=row[2],
                current_step_index=row[3],
                total_steps=row[4],
                started_at=datetime.fromisoformat(row[5]) if row[5] else None,
                completed_at=datetime.fromisoformat(row[6]) if row[6] else None,
                last_successful_step=row[7],
                errors=json.loads(row[8]) if row[8] else []
            )

            logger.info(f"Loaded workflow state: {workflow_run_id}")
            return state

        except Exception as e:
            logger.error(f"Failed to load workflow state: {e}", exc_info=True)
            return None

    @classmethod
    def create(cls, workflow_run_id: str, workflow_id: int, total_steps: int) -> 'WorkflowState':
        """
        Create a new workflow state.

        Args:
            workflow_run_id: Workflow run UUID
            workflow_id: Workflow definition ID
            total_steps: Total number of steps in workflow

        Returns:
            New WorkflowState instance
        """
        return cls(
            workflow_run_id=workflow_run_id,
            workflow_id=workflow_id,
            total_steps=total_steps,
            status="pending"
        )

    def __repr__(self) -> str:
        return (
            f"WorkflowState(run_id={self.workflow_run_id[:8]}..., "
            f"status={self.status}, "
            f"step={self.current_step_index}/{self.total_steps})"
        )
