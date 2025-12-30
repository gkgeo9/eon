#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shared navigation components for Fintel UI.
Provides consistent navigation patterns across all pages.
"""

import streamlit as st
from typing import Dict, Literal


def render_home_button(width: Literal["stretch", "content"] = "content"):
    """
    Render consistent home button.

    Args:
        width: Button width - "stretch" for full width, "content" for auto
    """
    if st.button("🏠 Back to Home", width=width):
        st.switch_page("streamlit_app.py")


def render_page_navigation(show_divider: bool = True):
    """
    Render standard page navigation footer.

    Args:
        show_divider: If True, show divider before navigation
    """
    if show_divider:
        st.markdown("---")

    render_home_button(width="content")


def render_multi_button_navigation(buttons: Dict[str, str], show_divider: bool = True):
    """
    Render multiple navigation buttons in columns.

    Args:
        buttons: Dictionary mapping button label to page path
            Example: {"🏠 Home": "streamlit_app.py", "📜 History": "pages/3_📈_Analysis_History.py"}
        show_divider: If True, show divider before navigation
    """
    if show_divider:
        st.markdown("---")

    if not buttons:
        return

    cols = st.columns(len(buttons))

    for col, (label, page) in zip(cols, buttons.items()):
        with col:
            if st.button(label, width="stretch"):
                st.switch_page(page)


def render_breadcrumb(items: list):
    """
    Render breadcrumb navigation.

    Args:
        items: List of tuples (label, page_path) or just labels for current page
            Example: [("Home", "streamlit_app.py"), ("Settings", None)]
    """
    breadcrumb_html = []

    for i, item in enumerate(items):
        if isinstance(item, tuple):
            label, page = item
            if page and i < len(items) - 1:
                # Clickable link (not last item)
                breadcrumb_html.append(f'<a href="#" onclick="return false;">{label}</a>')
            else:
                # Current page (last item) or no link
                breadcrumb_html.append(f'<span style="color: #888;">{label}</span>')
        else:
            breadcrumb_html.append(f'<span style="color: #888;">{item}</span>')

        if i < len(items) - 1:
            breadcrumb_html.append('<span style="margin: 0 0.5rem;">→</span>')

    st.markdown(
        f'<div style="font-size: 0.9rem; margin-bottom: 1rem;">{" ".join(breadcrumb_html)}</div>',
        unsafe_allow_html=True
    )
