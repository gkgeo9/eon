#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Prompt templates for fundamental analysis.

This module contains all prompt templates for fundamental 10-K analysis,
organized to match the corresponding Pydantic models in models/.
"""

from .basic import (
    DEFAULT_10K_PROMPT,
    DEEP_DIVE_PROMPT,
    FOCUSED_ANALYSIS_PROMPT,
)
from .success_factors import SUCCESS_FACTORS_PROMPT

__all__ = [
    'DEFAULT_10K_PROMPT',
    'DEEP_DIVE_PROMPT',
    'FOCUSED_ANALYSIS_PROMPT',
    'SUCCESS_FACTORS_PROMPT',
]
