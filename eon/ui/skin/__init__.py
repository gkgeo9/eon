#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EON UI skin package.

A presentation-only layer that restyles the existing Streamlit app to match
the "Erebus Observatory Network" design system (from Claude Design).

This package is purely cosmetic: it injects CSS to restyle Streamlit's native
widgets and renders a brand mark + dark/light toggle in the sidebar. It does
NOT touch any analysis, batch, database, or business logic -- it only reads
state (the chosen theme) and re-renders the existing UI with a new look.

Public API:
    apply_skin()  -- inject the design system and render the sidebar chrome.
"""

from .skin import apply_skin

__all__ = ["apply_skin"]
