#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Central registry of analysis types for EON.

This module provides a single source of truth for all analysis type definitions,
descriptions, and requirements. Both CLI and UI should reference this module
instead of defining analysis types inline.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class AnalysisTypeInfo:
    """Definition of an analysis type."""

    id: str
    name: str
    description: str
    icon: str = ""
    min_years: int = 1
    is_multi_year_aggregated: bool = False
    cli_choice: str = ""  # Click choice value (empty = same as id)

    @property
    def display_name(self) -> str:
        """Full display name with icon for UI."""
        if self.icon:
            return f"{self.icon} {self.name}"
        return self.name

    @property
    def cli_name(self) -> str:
        """Name to use in CLI Choice options."""
        return self.cli_choice or self.id


# ============================================================
# Built-in analysis type definitions
# ============================================================

ANALYSIS_TYPES: Dict[str, AnalysisTypeInfo] = {}


def _register(*types: AnalysisTypeInfo) -> None:
    for t in types:
        ANALYSIS_TYPES[t.id] = t


_register(
    AnalysisTypeInfo(
        id="fundamental",
        name="Fundamental Analysis",
        icon="📋",
        description="Analyzes business model, financials, risks, and key strategies.",
        min_years=1,
    ),
    AnalysisTypeInfo(
        id="excellent",
        name="Excellent Company Success Factors",
        icon="⭐",
        description=(
            "Multi-year analysis for proven winners - identifies what made "
            "excellent companies succeed. Requires at least 3 years."
        ),
        min_years=3,
        is_multi_year_aggregated=True,
    ),
    AnalysisTypeInfo(
        id="objective",
        name="Objective Company Analysis",
        icon="🎯",
        description=(
            "Multi-year unbiased analysis - objective assessment of any "
            "company's strengths and weaknesses. Requires at least 3 years."
        ),
        min_years=3,
        is_multi_year_aggregated=True,
    ),
    AnalysisTypeInfo(
        id="buffett",
        name="Buffett Lens",
        icon="💰",
        description=(
            "Warren Buffett perspective: economic moat, management quality, "
            "pricing power, and intrinsic value."
        ),
        min_years=1,
    ),
    AnalysisTypeInfo(
        id="taleb",
        name="Taleb Lens",
        icon="🛡️",
        description=(
            "Nassim Taleb perspective: fragility assessment, tail risks, "
            "and antifragility."
        ),
        min_years=1,
    ),
    AnalysisTypeInfo(
        id="contrarian",
        name="Contrarian Lens",
        icon="🔍",
        description=(
            "Contrarian perspective: variant perception, hidden opportunities, "
            "and market mispricings."
        ),
        min_years=1,
    ),
    AnalysisTypeInfo(
        id="multi",
        name="Multi-Perspective",
        icon="🎭",
        description=(
            "Combined analysis through all three investment lenses: "
            "Buffett, Taleb, and Contrarian."
        ),
        min_years=1,
    ),
    AnalysisTypeInfo(
        id="scanner",
        name="Contrarian Scanner",
        icon="💎",
        description=(
            "Six-dimension scoring system (0-600 scale) to identify companies "
            "with hidden compounder potential. Requires at least 3 years."
        ),
        min_years=3,
        is_multi_year_aggregated=True,
    ),
)

# IDs that require multi-year data
MULTI_YEAR_TYPES = frozenset(
    t.id for t in ANALYSIS_TYPES.values() if t.min_years >= 3
)

# Valid IDs for CLI --analysis-type choices
CLI_ANALYSIS_CHOICES: List[str] = [t.id for t in ANALYSIS_TYPES.values()]

# Default filing types shown when SEC query is not available
DEFAULT_FILING_TYPES: List[str] = ["10-K", "10-Q", "8-K", "4", "DEF 14A"]


def get_analysis_type(type_id: str) -> Optional[AnalysisTypeInfo]:
    """
    Look up an analysis type by its ID.

    Handles both built-in types and custom workflow prefixes (``custom:...``).

    Args:
        type_id: Analysis type identifier (e.g. ``"fundamental"``, ``"custom:my_wf"``)

    Returns:
        AnalysisTypeInfo for built-in types, or None for unknown/custom types.
    """
    return ANALYSIS_TYPES.get(type_id)


def is_valid_analysis_type(type_id: str) -> bool:
    """Check whether *type_id* is a known built-in or ``custom:`` type."""
    if type_id in ANALYSIS_TYPES:
        return True
    if type_id.startswith("custom:"):
        return True
    return False


def requires_multi_year(type_id: str) -> bool:
    """Return True if the analysis type needs >= 3 years of data."""
    info = ANALYSIS_TYPES.get(type_id)
    if info:
        return info.min_years >= 3
    return False


def get_ui_options(
    include_custom_workflows: bool = True,
    custom_workflows: Optional[List[dict]] = None,
) -> Tuple[List[str], Dict[str, str]]:
    """
    Build the (display_labels, label_to_id_map) for Streamlit selectboxes.

    Returns:
        A tuple of:
        - List of display labels (suitable for ``st.selectbox(options=...)``)
        - Dict mapping display label -> internal analysis type id
    """
    labels: List[str] = []
    label_map: Dict[str, str] = {}

    for info in ANALYSIS_TYPES.values():
        label = info.display_name
        labels.append(label)
        label_map[label] = info.id

    if include_custom_workflows and custom_workflows:
        labels.append("───── Custom Workflows ─────")
        for wf in custom_workflows:
            display = f"{wf['icon']} {wf['name']}"
            labels.append(display)
            label_map[display] = f"custom:{wf['id']}"

    return labels, label_map
