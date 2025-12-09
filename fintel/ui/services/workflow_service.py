#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WorkflowService - Service layer for workflow execution and management.

Provides a clean API for the Streamlit UI to:
- Create and save workflows
- Execute workflows
- Monitor workflow runs
- Get results
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import uuid
from datetime import datetime

from fintel.workflows.engine import WorkflowEngine, DataContainer
from fintel.ui.database import DatabaseRepository
from fintel.ui.services.analysis_service import AnalysisService
from fintel.core import get_logger


class WorkflowService:
    """
    Service for workflow execution and management.

    This is the primary interface for the UI to interact with
    the workflow execution engine.
    """

    def __init__(self, db: DatabaseRepository, analysis_service: AnalysisService):
        """
        Initialize workflow service.

        Args:
            db: Database repository instance
            analysis_service: Analysis service instance
        """
        self.db = db
        self.analysis_service = analysis_service
        self.engine = WorkflowEngine(db, analysis_service)
        self.logger = get_logger(__name__)

    def save_workflow(
        self,
        name: str,
        description: str,
        workflow_definition: Dict[str, Any]
    ) -> int:
        """
        Save workflow definition to database.

        Args:
            name: Workflow name (must be unique)
            description: Workflow description
            workflow_definition: Workflow JSON structure (with steps)

        Returns:
            Workflow ID

        Raises:
            ValueError: If workflow already exists
        """
        self.logger.info(f"Saving workflow: {name}")

        # Check if workflow exists
        existing = self._get_workflow_by_name(name)

        if existing:
            # Update existing workflow
            workflow_id = existing['id']
            query = """
                UPDATE workflows
                SET description = ?,
                    workflow_json = ?,
                    updated_at = ?
                WHERE id = ?
            """
            self.db._execute_with_retry(query, (
                description,
                json.dumps(workflow_definition),
                datetime.now().isoformat(),
                workflow_id
            ))
            self.logger.info(f"Updated existing workflow {workflow_id}: {name}")

        else:
            # Insert new workflow
            query = """
                INSERT INTO workflows (name, description, workflow_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """
            cursor = self.db._execute_with_retry(query, (
                name,
                description,
                json.dumps(workflow_definition),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            workflow_id = cursor.lastrowid
            self.logger.info(f"Created new workflow {workflow_id}: {name}")

        return workflow_id

    def execute_workflow(
        self,
        workflow_id: int,
        resume: bool = False,
        workflow_run_id: Optional[str] = None
    ) -> str:
        """
        Execute a workflow.

        Args:
            workflow_id: ID of workflow to execute
            resume: Resume from previous failed run
            workflow_run_id: Required if resume=True

        Returns:
            workflow_run_id: ID of this execution run

        Raises:
            ValueError: If workflow not found or resume parameters invalid
            WorkflowExecutionError: If workflow execution fails
        """
        if resume and not workflow_run_id:
            raise ValueError("workflow_run_id required for resume")

        if not resume:
            workflow_run_id = str(uuid.uuid4())

        self.logger.info(
            f"Executing workflow {workflow_id} (run_id: {workflow_run_id}, "
            f"resume: {resume})"
        )

        # Execute workflow (this may take a while)
        run_id = self.engine.execute_workflow(
            workflow_id=workflow_id,
            workflow_run_id=workflow_run_id,
            resume=resume
        )

        return run_id

    def get_run_status(self, workflow_run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a workflow run.

        Args:
            workflow_run_id: Workflow run UUID

        Returns:
            Status dictionary with current progress, or None if not found
        """
        return self.engine.get_workflow_status(workflow_run_id)

    def get_run_results(self, workflow_run_id: str) -> Optional[DataContainer]:
        """
        Get final results of completed workflow run.

        Args:
            workflow_run_id: Workflow run UUID

        Returns:
            DataContainer with results, or None if not found/completed
        """
        return self.engine.get_workflow_results(workflow_run_id)

    def list_workflows(self) -> List[Dict[str, Any]]:
        """
        List all saved workflows.

        Returns:
            List of workflow dictionaries
        """
        try:
            query = """
                SELECT id, name, description, created_at, updated_at
                FROM workflows
                ORDER BY updated_at DESC
            """
            cursor = self.db._execute_with_retry(query)
            rows = cursor.fetchall()

            workflows = []
            for row in rows:
                workflows.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'created_at': row[3],
                    'updated_at': row[4]
                })

            return workflows

        except Exception as e:
            self.logger.error(f"Failed to list workflows: {e}")
            return []

    def get_workflow(self, workflow_id: int) -> Optional[Dict[str, Any]]:
        """
        Get workflow definition by ID.

        Args:
            workflow_id: Workflow ID

        Returns:
            Workflow dictionary or None if not found
        """
        try:
            query = "SELECT * FROM workflows WHERE id = ?"
            cursor = self.db._execute_with_retry(query, (workflow_id,))
            row = cursor.fetchone()

            if row:
                workflow = dict(row)
                # Parse workflow_json
                workflow['workflow_json_parsed'] = json.loads(workflow['workflow_json'])
                return workflow

            return None

        except Exception as e:
            self.logger.error(f"Failed to get workflow {workflow_id}: {e}")
            return None

    def delete_workflow(self, workflow_id: int) -> bool:
        """
        Delete a workflow definition.

        Args:
            workflow_id: Workflow ID

        Returns:
            True if deleted successfully
        """
        try:
            query = "DELETE FROM workflows WHERE id = ?"
            self.db._execute_with_retry(query, (workflow_id,))
            self.logger.info(f"Deleted workflow {workflow_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete workflow {workflow_id}: {e}")
            return False

    def list_workflow_runs(
        self,
        workflow_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List workflow runs.

        Args:
            workflow_id: Optional filter by workflow ID
            limit: Maximum number of runs to return

        Returns:
            List of workflow run dictionaries
        """
        try:
            if workflow_id:
                query = """
                    SELECT * FROM workflow_run_details
                    WHERE workflow_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """
                params = (workflow_id, limit)
            else:
                query = """
                    SELECT * FROM workflow_run_details
                    ORDER BY created_at DESC
                    LIMIT ?
                """
                params = (limit,)

            cursor = self.db._execute_with_retry(query, params)
            rows = cursor.fetchall()

            runs = []
            for row in rows:
                runs.append(dict(row))

            return runs

        except Exception as e:
            self.logger.error(f"Failed to list workflow runs: {e}")
            return []

    def get_step_logs(
        self,
        workflow_run_id: str,
        step_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get execution logs for a workflow run.

        Args:
            workflow_run_id: Workflow run UUID
            step_id: Optional filter by step ID

        Returns:
            List of log entries
        """
        try:
            if step_id:
                query = """
                    SELECT step_id, log_level, message, created_at
                    FROM workflow_step_logs
                    WHERE workflow_run_id = ? AND step_id = ?
                    ORDER BY created_at ASC
                """
                params = (workflow_run_id, step_id)
            else:
                query = """
                    SELECT step_id, log_level, message, created_at
                    FROM workflow_step_logs
                    WHERE workflow_run_id = ?
                    ORDER BY created_at ASC
                """
                params = (workflow_run_id,)

            cursor = self.db._execute_with_retry(query, params)
            rows = cursor.fetchall()

            logs = []
            for row in rows:
                logs.append({
                    'step_id': row[0],
                    'log_level': row[1],
                    'message': row[2],
                    'created_at': row[3]
                })

            return logs

        except Exception as e:
            self.logger.error(f"Failed to get step logs: {e}")
            return []

    def _get_workflow_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get workflow by name."""
        try:
            query = "SELECT * FROM workflows WHERE name = ?"
            cursor = self.db._execute_with_retry(query, (name,))
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None

        except Exception as e:
            self.logger.error(f"Failed to get workflow by name: {e}")
            return None

    def export_workflow_to_file(self, workflow_id: int, file_path: Path) -> bool:
        """
        Export workflow definition to JSON file.

        Args:
            workflow_id: Workflow ID
            file_path: Path to save file

        Returns:
            True if exported successfully
        """
        try:
            workflow = self.get_workflow(workflow_id)

            if not workflow:
                self.logger.error(f"Workflow {workflow_id} not found")
                return False

            export_data = {
                'name': workflow['name'],
                'description': workflow['description'],
                'steps': json.loads(workflow['workflow_json']).get('steps', []),
                'created_at': workflow['created_at'],
                'exported_at': datetime.now().isoformat()
            }

            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2)

            self.logger.info(f"Exported workflow {workflow_id} to {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export workflow: {e}")
            return False

    def import_workflow_from_file(self, file_path: Path) -> Optional[int]:
        """
        Import workflow definition from JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            Workflow ID if imported successfully, None otherwise
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            name = data.get('name', file_path.stem)
            description = data.get('description', '')
            steps = data.get('steps', [])

            workflow_definition = {'steps': steps}

            workflow_id = self.save_workflow(name, description, workflow_definition)

            self.logger.info(f"Imported workflow from {file_path}: {workflow_id}")
            return workflow_id

        except Exception as e:
            self.logger.error(f"Failed to import workflow: {e}")
            return None
