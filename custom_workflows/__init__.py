#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Auto-discovery for custom analysis workflows.

Scans the custom_workflows/ directory for Python files containing
CustomWorkflow subclasses and registers them for use in the UI.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Dict, Type, List, Any, Optional
import logging

from .base import CustomWorkflow

logger = logging.getLogger(__name__)

# Registry of discovered workflows
_workflows: Dict[str, Type[CustomWorkflow]] = {}
_discovery_done: bool = False


def discover_workflows(workflows_dir: Optional[Path] = None, force: bool = False) -> Dict[str, Type[CustomWorkflow]]:
    """
    Discover all CustomWorkflow subclasses in the workflows directory.

    Args:
        workflows_dir: Directory to scan (defaults to this package's directory)
        force: If True, re-scan even if already discovered

    Returns:
        Dictionary mapping workflow_id to workflow class
    """
    global _workflows, _discovery_done

    if _discovery_done and not force:
        return _workflows

    if workflows_dir is None:
        workflows_dir = Path(__file__).parent

    _workflows.clear()

    # Scan for Python files in main directory
    _scan_directory(workflows_dir)

    # Also scan examples/ subdirectory
    examples_dir = workflows_dir / "examples"
    if examples_dir.exists():
        _scan_directory(examples_dir, prefix="examples.")

    _discovery_done = True
    return _workflows


def _scan_directory(directory: Path, prefix: str = "") -> None:
    """Scan a directory for workflow files."""
    global _workflows

    for py_file in directory.glob("*.py"):
        # Skip private files and base.py
        if py_file.name.startswith("_"):
            continue
        if py_file.name == "base.py":
            continue

        try:
            # Load module
            module_name = f"custom_workflows.{prefix}{py_file.stem}"
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Find CustomWorkflow subclasses
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, CustomWorkflow) and
                    attr is not CustomWorkflow):

                    # Use file stem as workflow ID
                    workflow_id = f"{prefix}{py_file.stem}" if prefix else py_file.stem
                    _workflows[workflow_id] = attr
                    logger.info(f"Discovered workflow: {attr.name} ({workflow_id})")

        except Exception as e:
            logger.error(f"Failed to load workflow from {py_file}: {e}")


def get_workflow(workflow_id: str) -> Optional[Type[CustomWorkflow]]:
    """
    Get a workflow class by ID.

    Args:
        workflow_id: The workflow identifier (file stem)

    Returns:
        The workflow class, or None if not found
    """
    if not _discovery_done:
        discover_workflows()
    return _workflows.get(workflow_id)


def list_workflows() -> List[Dict[str, Any]]:
    """
    List all available workflows with their metadata.

    Returns:
        List of workflow info dicts with keys: id, name, description, icon, min_years, category
    """
    if not _discovery_done:
        discover_workflows()

    return [
        {
            "id": workflow_id,
            "name": cls.name,
            "description": cls.description,
            "icon": cls.icon,
            "min_years": cls.min_years,
            "category": cls.category
        }
        for workflow_id, cls in sorted(_workflows.items(), key=lambda x: x[1].name)
    ]


def reload_workflows() -> Dict[str, Type[CustomWorkflow]]:
    """
    Force reload all workflows (useful after adding new files).

    Returns:
        Dictionary mapping workflow_id to workflow class
    """
    return discover_workflows(force=True)


# Export base class and functions
__all__ = [
    'CustomWorkflow',
    'discover_workflows',
    'get_workflow',
    'list_workflows',
    'reload_workflows',
]
