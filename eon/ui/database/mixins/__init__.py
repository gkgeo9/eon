#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database repository mixins for Single Responsibility Principle compliance.

Each mixin handles a specific domain of database operations, keeping
the main DatabaseRepository class focused and maintainable.
"""

from .runs import AnalysisRunsMixin
from .results import AnalysisResultsMixin
from .prompts import CustomPromptsMixin
from .cache import FileCacheMixin
from .settings import UserSettingsMixin
from .resume import ResumeMixin
from .statistics import StatisticsMixin
from .api_usage import APIUsageMixin
from .cik_cache import CIKCacheMixin
from .synthesis import SynthesisMixin

__all__ = [
    "AnalysisRunsMixin",
    "AnalysisResultsMixin",
    "CustomPromptsMixin",
    "FileCacheMixin",
    "UserSettingsMixin",
    "ResumeMixin",
    "StatisticsMixin",
    "APIUsageMixin",
    "CIKCacheMixin",
    "SynthesisMixin",
]
