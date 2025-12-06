#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pydantic models for comparative analysis.

Includes contrarian scanner models for identifying hidden gem
investment opportunities.
"""

from .contrarian_scores import (
    ContrarianScores,
    ContrarianAnalysis,
)

__all__ = [
    'ContrarianScores',
    'ContrarianAnalysis',
]
