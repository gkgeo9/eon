#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Erebus Observatory Network -- visual skin orchestrator.

Injects the design-system CSS (driven by the in-app dark/light toggle) and
renders the sidebar chrome. Everything is presentation-only; no app behaviour
changes. Pages additionally call :func:`eon.ui.skin.topbar` and the component
helpers to lay out their content in the design language.
"""

import streamlit as st

from .css import STATIC_CSS, theme_vars
from .chrome import render_sidebar, is_dark


def apply_skin() -> None:
    """Apply the Erebus design system and render the sidebar chrome."""
    st.markdown(
        f"<style>:root, .stApp {{{theme_vars(is_dark())}}}</style>",
        unsafe_allow_html=True,
    )
    st.markdown(f"<style>{STATIC_CSS}</style>", unsafe_allow_html=True)
    render_sidebar()
