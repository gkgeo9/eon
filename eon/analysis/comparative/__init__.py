"""
Comparative analysis modules for benchmarking and contrarian scanning.

This module provides tools for:
- Contrarian scanner: Find hidden gems using multi-year success factor analysis
- Benchmark comparator: Compare companies against top performers
"""

from eon.analysis.comparative.contrarian_scanner import (
    ContrarianScanner,
    ContrarianAnalysis,
    ContrarianScores,
)
from eon.analysis.comparative.benchmarking import BenchmarkComparator

__all__ = [
    "ContrarianScanner",
    "ContrarianAnalysis",
    "ContrarianScores",
    "BenchmarkComparator",
]
