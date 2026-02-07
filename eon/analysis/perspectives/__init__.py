#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Multi-perspective investment analysis module.
"""

from .schemas import (
    BuffettAnalysis,
    TalebAnalysis,
    ContrarianAnalysis,
    SimplifiedAnalysis,
)
from .analyzer import PerspectiveAnalyzer

__all__ = [
    "BuffettAnalysis",
    "TalebAnalysis",
    "ContrarianAnalysis",
    "SimplifiedAnalysis",
    "PerspectiveAnalyzer",
]
