#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Prompt templates for multi-perspective investment analysis.

Three investment philosophies:
- Warren Buffett (value, moat, management)
- Nassim Taleb (fragility, tail risks, antifragility)
- Contrarian View (variant perception)
"""

from .buffett import BUFFETT_PROMPT
from .taleb import TALEB_PROMPT
from .contrarian import CONTRARIAN_PROMPT
from .combined import MULTI_PERSPECTIVE_PROMPT

__all__ = [
    'BUFFETT_PROMPT',
    'TALEB_PROMPT',
    'CONTRARIAN_PROMPT',
    'MULTI_PERSPECTIVE_PROMPT',
]
