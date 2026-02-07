#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shared session state initialization for EON UI.
Ensures consistent initialization across all pages.
"""

import streamlit as st
from eon.ui.database import DatabaseRepository


def init_session_state():
    """
    Initialize shared session state variables.
    Call this at the top of every page after apply_theme().

    Initialized Variables:
        - db (DatabaseRepository): Shared database connection
        - page_initialized (dict): Tracks page initialization status

    Returns:
        DatabaseRepository instance for convenience
    """
    # Database repository (shared across all pages)
    if 'db' not in st.session_state:
        st.session_state.db = DatabaseRepository()

    # Common UI state
    if 'page_initialized' not in st.session_state:
        st.session_state.page_initialized = {}

    return st.session_state.db


def init_page_state(page_name: str, defaults: dict = None):
    """
    Initialize page-specific session state.

    Args:
        page_name: Unique page identifier
        defaults: Dictionary of default values for page state

    Example:
        init_page_state("settings", {
            "show_prompt_editor": False,
            "edit_prompt_id": None
        })
    """
    if page_name not in st.session_state.page_initialized:
        if defaults:
            for key, value in defaults.items():
                if key not in st.session_state:
                    st.session_state[key] = value

        st.session_state.page_initialized[page_name] = True


def get_or_create(key: str, default_value):
    """
    Get a session state value or create it with a default.

    Args:
        key: Session state key
        default_value: Value to set if key doesn't exist

    Returns:
        The value from session state
    """
    if key not in st.session_state:
        st.session_state[key] = default_value
    return st.session_state[key]


def clear_page_state(page_name: str):
    """
    Clear all state for a specific page.

    Args:
        page_name: Page identifier to clear
    """
    if page_name in st.session_state.page_initialized:
        del st.session_state.page_initialized[page_name]


def sync_run_state_with_db(run_id: str = None):
    """
    Synchronize session state with database for analysis runs.

    This function ensures that session state reflects the true status
    of analysis runs in the database. It handles cases where:
    - An analysis completed while the page was not active
    - The app was restarted during an analysis
    - Status changed due to external factors

    Args:
        run_id: Optional specific run ID to sync. If None, syncs current_run_id.

    Returns:
        dict with sync results: {synced: bool, old_status: str, new_status: str}
    """
    if 'db' not in st.session_state:
        return {'synced': False, 'error': 'Database not initialized'}

    db = st.session_state.db
    target_run_id = run_id or st.session_state.get('current_run_id')

    if not target_run_id:
        return {'synced': False, 'error': 'No run ID to sync'}

    # Get actual status from database
    db_status = db.get_run_status(target_run_id)
    session_status = st.session_state.get(f'run_status_{target_run_id}')

    result = {
        'synced': True,
        'run_id': target_run_id,
        'old_status': session_status,
        'new_status': db_status,
        'changed': session_status != db_status
    }

    # Update session state to match database
    if db_status:
        st.session_state[f'run_status_{target_run_id}'] = db_status

        # If this is the current run, update related state
        if target_run_id == st.session_state.get('current_run_id'):
            if db_status in ('completed', 'failed', 'cancelled'):
                # Analysis is done - update monitoring flags
                st.session_state['check_status'] = False

    return result


def cleanup_stale_runs():
    """
    Clean up session state for runs that are no longer active.

    This function removes session state for runs that have completed,
    failed, or been cancelled, freeing up memory and preventing stale
    state from affecting the UI.

    Returns:
        int: Number of stale runs cleaned up
    """
    if 'db' not in st.session_state:
        return 0

    db = st.session_state.db
    cleaned = 0

    # Find all run-related keys in session state
    run_keys = [k for k in st.session_state.keys() if k.startswith('run_status_')]

    for key in run_keys:
        run_id = key.replace('run_status_', '')
        db_status = db.get_run_status(run_id)

        # If run is terminal and not the current run, clean it up
        if db_status in ('completed', 'failed', 'cancelled'):
            if run_id != st.session_state.get('current_run_id'):
                del st.session_state[key]
                # Also clean up any related state
                related_keys = [
                    f'run_progress_{run_id}',
                    f'run_error_{run_id}',
                ]
                for rk in related_keys:
                    if rk in st.session_state:
                        del st.session_state[rk]
                cleaned += 1

    return cleaned
