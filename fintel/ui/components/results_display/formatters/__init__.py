#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Result formatters for different analysis types.
"""

from .base import BaseFormatter
from .fundamental import FundamentalFormatter

__all__ = [
    'BaseFormatter',
    'FundamentalFormatter',
]
