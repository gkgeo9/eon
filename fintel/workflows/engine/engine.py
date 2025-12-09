#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WorkflowEngine - Main orchestrator for workflow execution.
"""

from typing import Dict, Any, Optional
import json
import traceback
import uuid
from datetime import datetime

from .data_container import DataContainer
from .state import WorkflowState
from .executors import (
    StepExecutor,
    InputStepExecutor,
    FundamentalAnalysisExecutor,
    SuccessFactorsExecutor,
    PerspectiveAnalysisExecutor,
    CustomPromptExecutor,
    FilterExecutor,
    AggregateExecutor,
    ExportExecutor
)
from fintel.core import get_logger


class WorkflowExecutionError(Exception):
    """Raised when workflow execution fails."""
    pass


class WorkflowEngine:
    """
    Executes a workflow definition step-by-step.

    Responsibilities:
    - Load workflow JSON
    - Initialize workflow state
    - Execute steps in sequence
    - Pass data between steps
    - Handle errors and recovery
    - Save workflow run results
    """

    def __init__(self, db, analysis_service):
        """
        Initialize workflow engine.

        Args:
            db: DatabaseRepository instance
            analysis_service: AnalysisService instance
        """
        self.db = db
        self.analysis_service = analysis_service
        self.logger = get_logger(__name__)

        # Register step executors
        self.step_executors = self._register_executors()

    def _register_executors(self) -> Dict[str, type]:
        """
        Register all step executor classes.

        Returns:
            Dictionary mapping step type to executor class
        """
        return {
            'input': InputStepExecutor,
            'fundamental_analysis': FundamentalAnalysisExecutor,
            'success_factors': SuccessFactorsExecutor,
            'perspective_analysis': PerspectiveAnalysisExecutor,
            'custom_analysis': CustomPromptExecutor,
            'filter': FilterExecutor,
            'aggregate': AggregateExecutor,
            'export': ExportExecutor
        }

    def execute_workflow(
        self,
        workflow_id: int,
        workflow_run_id: Optional[str] = None,
        resume: bool = False
    ) -> str:
        """
        Execute entire workflow.

        Args:
            workflow_id: Workflow definition ID from database
            workflow_run_id: Optional workflow run ID (required if resume=True)
            resume: Resume from previous failed run

        Returns:
            workflow_run_id for tracking

        Raises:
            WorkflowExecutionError: If workflow fails
        """
        # Load workflow definition
        workflow = self._load_workflow(workflow_id)

        if not workflow:
            raise WorkflowExecutionError(f"Workflow {workflow_id} not found")

        workflow_json = json.loads(workflow['workflow_json'])
        steps = workflow_json.get('steps', [])

        if not steps:
            raise WorkflowExecutionError("Workflow has no steps")

        # Initialize or resume state
        if resume:
            if not workflow_run_id:
                raise ValueError("workflow_run_id required for resume")

            state = WorkflowState.load(workflow_run_id, self.db)

            if not state:
                raise WorkflowExecutionError(f"Cannot resume: run {workflow_run_id} not found")

            self.logger.info(
                f"Resuming workflow run {workflow_run_id} from step "
                f"{state.current_step_index}"
            )
            start_index = state.current_step_index
            current_data = state.load_step_output(state.last_successful_step, self.db) if state.last_successful_step else None

        else:
            # Create new run
            if not workflow_run_id:
                workflow_run_id = str(uuid.uuid4())

            state = WorkflowState.create(
                workflow_run_id=workflow_run_id,
                workflow_id=workflow_id,
                total_steps=len(steps)
            )
            state.started_at = datetime.now()
            state.status = 'running'
            state.save(self.db)

            self.logger.info(
                f"Starting new workflow run {workflow_run_id}: "
                f"{workflow['name']} ({len(steps)} steps)"
            )
            start_index = 0
            current_data = None

        # Execute steps
        for i in range(start_index, len(steps)):
            step = steps[i]
            step_id = step.get('step_id', f'step_{i+1}')

            state.current_step_index = i
            state.save(self.db)

            self.logger.info(f"Executing step {i+1}/{len(steps)}: {step_id}")

            try:
                # Log step start
                state.log_step(step_id, 'INFO', f'Starting step: {step_id}', self.db)

                # Execute step
                output = self.execute_step(step, current_data)

                # Save step output
                state.save_step_output(step_id, output, self.db)
                state.last_successful_step = step_id

                # Log success
                state.log_step(
                    step_id, 'INFO',
                    f'Step complete: shape={output.shape}, items={output.total_items}',
                    self.db
                )

                # Update current data for next step
                current_data = output

            except Exception as e:
                error_msg = f"Step {step_id} failed: {str(e)}"
                error_details = {
                    'step_id': step_id,
                    'step_index': i,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }

                self.logger.error(error_msg, exc_info=True)

                # Log error
                state.log_step(step_id, 'ERROR', error_msg, self.db)
                state.add_error(step_id, error_msg, error_details)

                # Update status and save
                state.status = 'failed'
                state.save(self.db)

                raise WorkflowExecutionError(f"Failed at step {i+1}: {step_id}") from e

        # Workflow completed successfully
        state.status = 'completed'
        state.completed_at = datetime.now()
        state.current_step_index = len(steps)
        state.save(self.db)

        self.logger.info(
            f"Workflow run {workflow_run_id} completed successfully "
            f"({len(steps)} steps)"
        )

        return workflow_run_id

    def execute_step(
        self,
        step_config: Dict[str, Any],
        input_data: Optional[DataContainer]
    ) -> DataContainer:
        """
        Execute a single workflow step.

        Args:
            step_config: Step configuration dictionary
            input_data: Input DataContainer (None for first step)

        Returns:
            Output DataContainer

        Raises:
            ValueError: If step configuration is invalid
            RuntimeError: If step execution fails
        """
        step_type = step_config.get('type')
        step_id = step_config.get('step_id', 'unknown')
        config = step_config.get('config', {})

        # Add step_id to config for executor use
        config['step_id'] = step_id

        self.logger.info(f"Executing step: {step_id} (type: {step_type})")

        # Get appropriate executor
        executor_class = self.step_executors.get(step_type)

        if not executor_class:
            raise ValueError(f"Unknown step type: {step_type}")

        # Create executor instance
        executor = executor_class(
            db=self.db,
            analysis_service=self.analysis_service
        )

        # Validate input
        try:
            executor.validate_input(input_data)
        except Exception as e:
            raise ValueError(
                f"Step {step_id} ({step_type}) input validation failed: {e}"
            )

        # Execute step
        try:
            output = executor.execute(config, input_data)

            # Validate output
            if not isinstance(output, DataContainer):
                raise RuntimeError(
                    f"Step {step_id} returned invalid output type: "
                    f"{type(output).__name__}"
                )

            return output

        except Exception as e:
            self.logger.error(f"Step {step_id} execution failed: {e}", exc_info=True)
            raise

    def _load_workflow(self, workflow_id: int) -> Optional[Dict[str, Any]]:
        """
        Load workflow definition from database.

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
                return dict(row)
            return None

        except Exception as e:
            self.logger.error(f"Failed to load workflow {workflow_id}: {e}")
            return None

    def get_workflow_status(self, workflow_run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a workflow run.

        Args:
            workflow_run_id: Workflow run UUID

        Returns:
            Status dictionary or None if not found
        """
        state = WorkflowState.load(workflow_run_id, self.db)

        if not state:
            return None

        # Get workflow name
        workflow = self._load_workflow(state.workflow_id)
        workflow_name = workflow['name'] if workflow else 'Unknown'

        return {
            'workflow_run_id': state.workflow_run_id,
            'workflow_id': state.workflow_id,
            'workflow_name': workflow_name,
            'status': state.status,
            'current_step': state.current_step_index,
            'total_steps': state.total_steps,
            'progress_percent': int((state.current_step_index / state.total_steps) * 100) if state.total_steps > 0 else 0,
            'started_at': state.started_at.isoformat() if state.started_at else None,
            'completed_at': state.completed_at.isoformat() if state.completed_at else None,
            'last_successful_step': state.last_successful_step,
            'errors': state.errors
        }

    def get_workflow_results(self, workflow_run_id: str) -> Optional[DataContainer]:
        """
        Get final results of completed workflow run.

        Args:
            workflow_run_id: Workflow run UUID

        Returns:
            Final DataContainer or None
        """
        state = WorkflowState.load(workflow_run_id, self.db)

        if not state:
            return None

        if state.status != 'completed':
            self.logger.warning(
                f"Workflow run {workflow_run_id} not completed (status: {state.status})"
            )
            return None

        # Get last step output
        if state.last_successful_step:
            return state.load_step_output(state.last_successful_step, self.db)

        return None
