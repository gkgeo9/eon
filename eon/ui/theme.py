#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Theme utilities for EON UI.

Styling is delegated to the presentation-only ``eon.ui.skin`` package, which
implements the "Erebus Observatory Network" design system (Geist / Fraunces
type, navy oklch palette, sidebar brand, card metrics, restyled widgets) and a
custom in-app dark/light toggle. The skin is purely cosmetic and does not alter
any app behaviour.

``apply_theme`` is kept as the stable entry point so every page picks up the
skin automatically without per-page changes.
"""

from eon.ui.skin import apply_skin


def apply_theme():
    """
    Apply consistent styling across all pages via the Erebus skin.

    Delegates to :func:`eon.ui.skin.apply_skin`, which injects the design system
    CSS (driven by the in-app dark/light toggle) and renders the sidebar brand.
    """
    apply_skin()
