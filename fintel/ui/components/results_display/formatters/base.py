#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Base formatter class for analysis results display.
Provides common patterns and utilities for all formatters.
"""

import streamlit as st
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod


class BaseFormatter(ABC):
    """Base class for all result formatters."""

    def __init__(self, result_data: Dict[str, Any]):
        """
        Initialize formatter with result data.

        Args:
            result_data: Dictionary containing analysis results
        """
        self.result_data = result_data

    @abstractmethod
    def render(self):
        """Render the formatted results. Must be implemented by subclasses."""
        pass

    def render_section(self, title: str, content: Any, collapsible: bool = False, expanded: bool = True):
        """
        Render a formatted section with consistent styling.

        Args:
            title: Section title
            content: Content to display (string, dict, list, etc.)
            collapsible: If True, wrap in expander
            expanded: Default expanded state (only if collapsible)
        """
        if collapsible:
            with st.expander(f"📊 {title}", expanded=expanded):
                self._render_content(content)
        else:
            st.subheader(f"📊 {title}")
            self._render_content(content)

    def _render_content(self, content: Any):
        """Render content based on type."""
        if isinstance(content, str):
            st.markdown(content)
        elif isinstance(content, dict):
            for key, value in content.items():
                if isinstance(value, (list, dict)):
                    st.markdown(f"**{key}:**")
                    st.json(value)
                else:
                    st.markdown(f"**{key}:** {value}")
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    st.json(item)
                else:
                    st.markdown(f"- {item}")
        else:
            st.write(content)

    def render_metric_card(self, label: str, value: Any, delta: Optional[str] = None, help_text: Optional[str] = None):
        """
        Render a metric card with enhanced styling.

        Args:
            label: Metric label
            value: Metric value
            delta: Optional delta value
            help_text: Optional help text
        """
        st.metric(label=label, value=value, delta=delta, help=help_text)

    def render_key_insights(self, insights: List[str], icon: str = "💡"):
        """
        Render key insights with visual emphasis.

        Args:
            insights: List of insight strings
            icon: Icon to use for each insight
        """
        st.markdown("### Key Insights")
        for insight in insights:
            st.info(f"{icon} {insight}")

    def render_empty_state(self, message: str = "No data available", show_icon: bool = True):
        """
        Render empty state with helpful guidance.

        Args:
            message: Message to display
            show_icon: Whether to show icon
        """
        icon = "📭 " if show_icon else ""
        st.info(f"{icon}{message}")

    def render_copy_button(self, text: str, label: str = "Copy to Clipboard"):
        """
        Render a copy-to-clipboard button.

        Args:
            text: Text to copy
            label: Button label
        """
        # Note: Streamlit doesn't have native clipboard support
        # This creates a text area that users can select and copy
        with st.expander("📋 Copy Data"):
            st.code(text, language="text")

    def render_tabs(self, tabs_config: Dict[str, callable]):
        """
        Render tabbed interface.

        Args:
            tabs_config: Dictionary mapping tab name to render function
        """
        tabs = st.tabs(list(tabs_config.keys()))
        for tab, (name, render_func) in zip(tabs, tabs_config.items()):
            with tab:
                render_func()

    def highlight_score(self, score: float, label: str, max_score: float = 100):
        """
        Render a score with color-coded highlighting.

        Args:
            score: Score value
            label: Score label
            max_score: Maximum possible score
        """
        percentage = (score / max_score) * 100

        if percentage >= 80:
            color = "green"
            icon = "🟢"
        elif percentage >= 60:
            color = "blue"
            icon = "🔵"
        elif percentage >= 40:
            color = "orange"
            icon = "🟠"
        else:
            color = "red"
            icon = "🔴"

        st.markdown(
            f'<div style="padding: 1rem; border-left: 4px solid {color}; background-color: rgba(0,0,0,0.05); border-radius: 0.5rem;">'
            f'<strong>{icon} {label}:</strong> {score:.1f}/{max_score}'
            f'</div>',
            unsafe_allow_html=True
        )

    def render_loading_skeleton(self, num_rows: int = 3):
        """
        Render loading skeleton for better perceived performance.

        Args:
            num_rows: Number of skeleton rows to show
        """
        for _ in range(num_rows):
            st.markdown(
                '<div style="height: 20px; background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); '
                'border-radius: 4px; margin: 10px 0; animation: shimmer 1.5s infinite;"></div>',
                unsafe_allow_html=True
            )
