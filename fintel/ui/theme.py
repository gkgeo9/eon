#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Theme utilities for Fintel UI.

Streamlit handles dark/light mode natively through:
1. User's system preference (automatic)
2. .streamlit/config.toml settings
3. Streamlit Cloud settings

This module provides minimal shared styling.
"""

import streamlit as st


def apply_theme():
    """
    Apply consistent styling across all pages.

    Note: Dark/light mode is handled by Streamlit natively.
    Configure in .streamlit/config.toml or let it follow system preference.
    """
    st.markdown("""
    <style>
    /* Consistent button styling */
    .stButton button {
        border-radius: 0.5rem;
        transition: all 0.2s ease;
    }

    .stButton button:hover {
        transform: translateY(-1px);
    }

    /* Form styling */
    .stForm {
        border-radius: 0.75rem;
        padding: 1.5rem;
    }

    /* Metric cards */
    .stMetric {
        padding: 1rem;
        border-radius: 0.75rem;
    }

    /* DataFrames */
    .stDataFrame {
        border-radius: 0.5rem;
        overflow: hidden;
    }

    /* Expanders */
    .stExpander {
        border-radius: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)
