#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analytics Dashboard - Insights into analysis patterns and trends.
Provides visual analytics for understanding usage patterns and API consumption.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from fintel.ui.theme import apply_theme
from fintel.ui.session import init_session_state
from fintel.ui.components.navigation import render_page_navigation

# Apply global theme
apply_theme()

# Initialize session state
db = init_session_state()

st.title("📊 Analytics Dashboard")
st.markdown("Insights into your analysis patterns, trends, and API usage")

st.markdown("---")

# Date range selector
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input(
        "Start Date",
        value=datetime.now() - timedelta(days=30),
        max_value=datetime.now()
    )
with col2:
    end_date = st.date_input(
        "End Date",
        value=datetime.now(),
        max_value=datetime.now()
    )

st.markdown("---")

# Create tabs for different analytics views
tab1, tab2, tab3, tab4 = st.tabs(["📈 Overview", "🎯 Analysis Trends", "⚡ Performance", "🔑 API Usage"])

with tab1:
    st.subheader("Overview Metrics")

    # Get analysis runs summary
    query = """
    SELECT
        COUNT(*) as total_runs,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
        SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running
    FROM analysis_runs
    WHERE created_at >= ? AND created_at <= ?
    """

    try:
        stats = db._execute_with_retry(
            query,
            params=(start_date.isoformat(), end_date.isoformat())
        ).fetchone()

        # Display key metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Total Analyses",
                stats['total_runs'] if stats else 0,
                help="Total number of analysis runs"
            )

        with col2:
            completed = stats['completed'] if stats else 0
            st.metric(
                "✅ Completed",
                completed,
                help="Successfully completed analyses"
            )

        with col3:
            failed = stats['failed'] if stats else 0
            st.metric(
                "❌ Failed",
                failed,
                delta=f"-{failed}" if failed > 0 else None,
                delta_color="inverse",
                help="Failed analyses"
            )

        with col4:
            total = stats['total_runs'] if stats else 0
            success_rate = (completed / total * 100) if total > 0 else 0
            st.metric(
                "Success Rate",
                f"{success_rate:.1f}%",
                help="Percentage of successful analyses"
            )

    except Exception as e:
        st.error(f"Error fetching overview metrics: {e}")

    st.markdown("---")

    # Most analyzed tickers
    st.subheader("🔝 Top Analyzed Tickers")

    query = """
    SELECT ticker, COUNT(*) as count
    FROM analysis_runs
    WHERE created_at >= ? AND created_at <= ?
    GROUP BY ticker
    ORDER BY count DESC
    LIMIT 10
    """

    try:
        top_tickers = db._execute_query(
            query,
            params=(start_date.isoformat(), end_date.isoformat())
        )

        if not top_tickers.empty:
            # Create bar chart
            st.bar_chart(top_tickers.set_index('ticker'))
        else:
            st.info("No analysis data available for the selected date range")

    except Exception as e:
        st.error(f"Error fetching top tickers: {e}")

with tab2:
    st.subheader("Analysis Trends Over Time")

    # Analysis volume over time
    query = """
    SELECT DATE(created_at) as date, COUNT(*) as count
    FROM analysis_runs
    WHERE created_at >= ? AND created_at <= ?
    GROUP BY DATE(created_at)
    ORDER BY date
    """

    try:
        trends = db._execute_query(
            query,
            params=(start_date.isoformat(), end_date.isoformat())
        )

        if not trends.empty:
            trends['date'] = pd.to_datetime(trends['date'])
            st.line_chart(trends.set_index('date'))
        else:
            st.info("No trend data available for the selected date range")

    except Exception as e:
        st.error(f"Error fetching trends: {e}")

    st.markdown("---")

    # Analysis type distribution
    st.subheader("📊 Analysis Type Distribution")

    query = """
    SELECT analysis_type, COUNT(*) as count
    FROM analysis_runs
    WHERE created_at >= ? AND created_at <= ?
    GROUP BY analysis_type
    ORDER BY count DESC
    """

    try:
        type_dist = db._execute_query(
            query,
            params=(start_date.isoformat(), end_date.isoformat())
        )

        if not type_dist.empty:
            # Display as pie chart (using Streamlit's built-in chart)
            st.bar_chart(type_dist.set_index('analysis_type'))

            # Also show as table
            st.markdown("**Breakdown:**")
            st.dataframe(
                type_dist,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "analysis_type": st.column_config.TextColumn("Analysis Type"),
                    "count": st.column_config.NumberColumn("Count", format="%d")
                }
            )
        else:
            st.info("No analysis type data available")

    except Exception as e:
        st.error(f"Error fetching analysis types: {e}")

with tab3:
    st.subheader("⚡ Performance Metrics")

    st.info("💡 Performance metrics help identify bottlenecks and optimization opportunities")

    # Average analysis time by type
    st.markdown("**Average Completion Time by Analysis Type**")

    query = """
    SELECT
        analysis_type,
        AVG(julianday(completed_at) - julianday(started_at)) * 24 * 60 as avg_minutes
    FROM analysis_runs
    WHERE status = 'completed'
    AND started_at IS NOT NULL
    AND completed_at IS NOT NULL
    AND created_at >= ? AND created_at <= ?
    GROUP BY analysis_type
    ORDER BY avg_minutes DESC
    """

    try:
        perf = db._execute_query(
            query,
            params=(start_date.isoformat(), end_date.isoformat())
        )

        if not perf.empty:
            # Format as readable times
            perf['avg_minutes'] = perf['avg_minutes'].round(2)

            st.dataframe(
                perf,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "analysis_type": st.column_config.TextColumn("Analysis Type"),
                    "avg_minutes": st.column_config.NumberColumn("Avg Time (minutes)", format="%.2f")
                }
            )
        else:
            st.info("No performance data available")

    except Exception as e:
        st.error(f"Error fetching performance metrics: {e}")

    st.markdown("---")

    # Success rate by analysis type
    st.markdown("**Success Rate by Analysis Type**")

    query = """
    SELECT
        analysis_type,
        COUNT(*) as total,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
        ROUND(CAST(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100, 1) as success_rate
    FROM analysis_runs
    WHERE created_at >= ? AND created_at <= ?
    GROUP BY analysis_type
    ORDER BY success_rate DESC
    """

    try:
        success = db._execute_query(
            query,
            params=(start_date.isoformat(), end_date.isoformat())
        )

        if not success.empty:
            st.dataframe(
                success,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "analysis_type": st.column_config.TextColumn("Analysis Type"),
                    "total": st.column_config.NumberColumn("Total Runs"),
                    "completed": st.column_config.NumberColumn("Completed"),
                    "success_rate": st.column_config.NumberColumn("Success Rate (%)", format="%.1f%%")
                }
            )
        else:
            st.info("No success rate data available")

    except Exception as e:
        st.error(f"Error fetching success rates: {e}")

with tab4:
    st.subheader("🔑 API Usage Tracking")

    st.warning("⚠️ API usage tracking requires integration with your API key management system")

    # Estimated API calls
    st.markdown("**Estimated API Calls (Based on Completed Analyses)**")

    query = """
    SELECT
        DATE(completed_at) as date,
        COUNT(*) * years_analyzed as estimated_calls
    FROM analysis_runs
    WHERE status = 'completed'
    AND completed_at >= ? AND completed_at <= ?
    GROUP BY DATE(completed_at)
    ORDER BY date
    """

    try:
        api_usage = db._execute_query(
            query,
            params=(start_date.isoformat(), end_date.isoformat())
        )

        if not api_usage.empty:
            api_usage['date'] = pd.to_datetime(api_usage['date'])
            st.line_chart(api_usage.set_index('date'))

            # Total estimated calls
            total_calls = api_usage['estimated_calls'].sum()
            st.metric("Total Estimated API Calls", f"{total_calls:,}")
        else:
            st.info("No API usage data available")

    except Exception as e:
        st.error(f"Error fetching API usage: {e}")

    st.markdown("---")

    # Cost estimation (placeholder)
    st.markdown("**💰 Cost Estimation**")
    st.info("💡 Integrate with your API provider's billing to track actual costs")

# Navigation
render_page_navigation()
