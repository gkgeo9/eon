#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shared session state initialization for Fintel UI.
Ensures consistent initialization across all pages.
"""

import streamlit as st
from fintel.ui.database import DatabaseRepository


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
