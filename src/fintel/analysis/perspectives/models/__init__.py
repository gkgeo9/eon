#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pydantic models for multi-perspective investment analysis.

Three investment philosophies:
- Warren Buffett (value, moat, management)
- Nassim Taleb (fragility, tail risks, antifragility)
- Contrarian View (variant perception)
"""

from .buffett import BuffettAnalysis
from .taleb import TalebAnalysis
from .contrarian import ContrarianViewAnalysis
from .combined import MultiPerspectiveAnalysis

__all__ = [
    'BuffettAnalysis',
    'TalebAnalysis',
    'ContrarianViewAnalysis',
    'MultiPerspectiveAnalysis',
]
