#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EON UI skin package.

A presentation-only layer that re-skins the existing Streamlit app to match the
"Erebus Observatory Network" design system (from Claude Design): sidebar brand +
custom nav, top breadcrumb bar, dark/light toggle, and a library of design
components (page headers, KPI cards, pills, dense tables, verdict cards, segment
bars, charts).

This package is purely cosmetic -- it reads already-computed data and renders it
in the design language. It does NOT touch analysis, batch, database, or business
logic.

Public API:
    apply_skin()  -- inject the design system + sidebar chrome (called by
                     ``eon.ui.theme.apply_theme`` so every page picks it up).
    topbar(...)   -- render the breadcrumb top bar for a page.
    components    -- design component helpers (page_header, kpi_grid, pill, ...).
"""

from .skin import apply_skin
from .chrome import topbar, is_dark
from . import components

__all__ = ["apply_skin", "topbar", "is_dark", "components"]
