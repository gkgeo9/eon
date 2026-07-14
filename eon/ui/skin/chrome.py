#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
App chrome for the Erebus skin: sidebar (brand + custom nav + theme toggle) and
the top breadcrumb bar. Navigation uses ``st.page_link`` so real page switching
keeps working; the default Streamlit page nav is hidden via CSS.
"""

from typing import List, Optional

import streamlit as st

THEME_KEY = "eon_theme"
_DARK = "🌙 Dark"
_LIGHT = "☀️ Light"

# Brand mark redrawn in SVG (theme-aware).
_BRAND_SVG = """
<svg viewBox="0 0 40 40" width="26" height="26" fill="none">
  <path d="M12 8 L20 4 L28 8 L28 32 L20 36 L12 32 Z" stroke="var(--logo-fg)" stroke-width="1.4" stroke-linejoin="round" opacity="0.55"/>
  <path d="M16 13 L20 11 L24 13 L24 27 L20 29 L16 27 Z" stroke="var(--logo-fg)" stroke-width="1" stroke-linejoin="round" opacity="0.35"/>
  <circle cx="20" cy="14" r="2.3" fill="oklch(0.96 0.10 240)"/>
  <circle cx="20" cy="14" r="4" fill="oklch(0.78 0.16 240)" opacity="0.4"/>
  <path d="M19 18 L19 26 M21 18 L21 26 M17 22 L23 22" stroke="var(--logo-fg)" stroke-width="1.2" stroke-linecap="round" opacity="0.7"/>
</svg>
"""

# (entrypoint-relative path, label, material icon)
_NAV = [
    ("streamlit_app.py", "Dashboard", ":material/dashboard:"),
    ("pages/1_📊_Analysis.py", "Analysis Engine", ":material/analytics:"),
    ("pages/2_📈_Analysis_History.py", "Analysis History", ":material/history:"),
    ("pages/3_🔍_Results_Viewer.py", "Results Viewer", ":material/search:"),
    ("pages/4_🌙_Batch_Queue.py", "Batch Queue", ":material/grid_view:"),
    ("pages/5_⚙️_Settings.py", "Settings & Database", ":material/settings:"),
]


def is_dark() -> bool:
    """Return True if the dark theme is currently selected (default)."""
    return st.session_state.get(THEME_KEY, _DARK) == _DARK


def render_sidebar() -> None:
    """Render brand, custom navigation, and the dark/light toggle."""
    with st.sidebar:
        st.markdown(
            f'<div class="eon-brand"><div class="mark">{_BRAND_SVG}</div>'
            f'<div class="txt"><span class="name">Erebus</span>'
            f'<span class="sub">Observatory Network</span></div></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="eon-navsection">Workspace</div>', unsafe_allow_html=True)
        for path, label, icon in _NAV:
            try:
                st.page_link(path, label=label, icon=icon)
            except Exception:
                # Page not found (e.g. running a single page in isolation) — skip.
                pass

        st.markdown('<div class="eon-navsection">Appearance</div>', unsafe_allow_html=True)
        st.markdown('<div class="eon-theme-toggle">', unsafe_allow_html=True)
        st.radio(
            "Theme",
            options=[_DARK, _LIGHT],
            horizontal=True,
            label_visibility="collapsed",
            key=THEME_KEY,
        )
        st.markdown("</div>", unsafe_allow_html=True)


def topbar(crumbs: List[str], status: Optional[str] = None) -> None:
    """
    Render the top breadcrumb bar at the top of a page's content.

    ``crumbs`` are joined with separators; the last is highlighted as current.
    ``status`` defaults to an EDGAR/version indicator like the design.
    """
    parts = []
    for i, c in enumerate(crumbs):
        last = i == len(crumbs) - 1
        parts.append(f'<span class="{"cur" if last else ""}">{c}</span>')
        if not last:
            parts.append('<span class="sep">/</span>')
    crumb_html = "".join(parts)
    if status is None:
        status = '<span style="color:var(--success)">●</span> EDGAR 200 OK &nbsp; v0.1.0'
    st.markdown(
        f'<div class="eon"><div class="eon-topbar"><div class="eon-crumbs">{crumb_html}</div>'
        f'<div class="eon-status">{status}</div></div></div>',
        unsafe_allow_html=True,
    )
