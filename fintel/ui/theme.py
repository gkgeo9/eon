#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Global theme management for Fintel UI.
Import and call apply_theme() at the top of every page.
"""

import streamlit as st
from fintel.ui.database import DatabaseRepository


def apply_theme():
    """
    Apply global theme based on user preference.
    Call this at the top of every Streamlit page.
    """
    # Initialize db if needed
    if 'db' not in st.session_state:
        st.session_state.db = DatabaseRepository()

    db = st.session_state.db

    # Get theme preference
    theme = db.get_setting("theme", default="light")

    # Apply dark mode CSS if enabled
    if theme == "dark":
        st.markdown("""
        <style>
        /* ========================================
           FINTEL DARK MODE - Polished & Professional
           ======================================== */

        /* Main app background */
        .stApp {
            background-color: #0e1117;
            color: #fafafa;
        }

        .stApp header {
            background-color: #0e1117;
        }

        /* Text elements - preserve hierarchy */
        .stMarkdown, .stText {
            color: #fafafa;
        }

        h1, h2, h3, h4, h5, h6 {
            color: #fafafa !important;
        }

        p {
            color: #e5e7eb;
        }

        /* Links */
        a {
            color: #60a5fa;
            text-decoration: none;
        }

        a:hover {
            color: #93c5fd;
            text-decoration: underline;
        }

        /* Caption and muted text */
        .stCaption {
            color: #9ca3af !important;
        }

        /* ========================================
           BUTTONS - Rounded & Polished
           ======================================== */

        .stButton button {
            background-color: #1f2937;
            color: #fafafa;
            border: 1px solid #374151;
            border-radius: 0.5rem;
            padding: 0.5rem 1rem;
            font-weight: 500;
            transition: all 0.2s ease;
        }

        .stButton button:hover {
            background-color: #374151;
            border-color: #4b5563;
            transform: translateY(-1px);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }

        .stButton button[kind="primary"] {
            background-color: #3b82f6;
            border-color: #3b82f6;
        }

        .stButton button[kind="primary"]:hover {
            background-color: #2563eb;
            border-color: #2563eb;
        }

        .stButton button[kind="secondary"] {
            background-color: #4b5563;
            border-color: #6b7280;
        }

        .stDownloadButton button {
            background-color: #10b981;
            border-color: #10b981;
            color: white;
            border-radius: 0.5rem;
        }

        .stDownloadButton button:hover {
            background-color: #059669;
            border-color: #059669;
        }

        /* ========================================
           INPUT FIELDS - Rounded & Styled
           ======================================== */

        /* Select boxes */
        div[data-baseweb="select"] > div {
            background-color: #1f2937 !important;
            color: #fafafa !important;
            border-radius: 0.5rem !important;
            border: 1px solid #374151 !important;
        }

        div[data-baseweb="select"] ul {
            background-color: #1f2937 !important;
            border: 1px solid #374151 !important;
            border-radius: 0.5rem !important;
        }

        div[data-baseweb="select"] li {
            background-color: #1f2937 !important;
            color: #fafafa !important;
        }

        div[data-baseweb="select"] li:hover {
            background-color: #374151 !important;
        }

        /* Text inputs, text areas, number inputs */
        div[data-baseweb="input"] > div,
        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input {
            background-color: #1f2937 !important;
            color: #fafafa !important;
            border-radius: 0.5rem !important;
            border: 1px solid #374151 !important;
        }

        .stTextInput input:focus,
        .stTextArea textarea:focus,
        .stNumberInput input:focus {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 1px #3b82f6 !important;
        }

        /* Labels */
        .stSelectbox label,
        .stTextInput label,
        .stTextArea label,
        .stNumberInput label,
        .stRadio label,
        .stCheckbox label {
            color: #fafafa !important;
            font-weight: 500;
        }

        /* Radio buttons */
        .stRadio > div {
            background-color: transparent;
        }

        .stRadio > div > label > div {
            color: #fafafa !important;
        }

        /* Checkboxes */
        .stCheckbox > label {
            color: #fafafa !important;
        }

        /* Sliders */
        .stSlider > div > div > div {
            color: #fafafa;
        }

        /* ========================================
           DATAFRAMES & TABLES - Properly Styled
           ======================================== */

        /* DataFrame container */
        .stDataFrame {
            border-radius: 0.5rem;
            overflow: hidden;
        }

        /* Table styling */
        .stDataFrame table {
            background-color: #1f2937 !important;
            border-radius: 0.5rem;
        }

        /* Table headers */
        .stDataFrame thead tr th {
            background-color: #374151 !important;
            color: #fafafa !important;
            font-weight: 600;
            padding: 0.75rem 1rem;
            border-bottom: 2px solid #4b5563 !important;
        }

        /* Table rows */
        .stDataFrame tbody tr {
            background-color: #1f2937 !important;
            border-bottom: 1px solid #374151 !important;
        }

        .stDataFrame tbody tr:hover {
            background-color: #374151 !important;
        }

        /* Table cells */
        .stDataFrame tbody tr td {
            color: #e5e7eb !important;
            padding: 0.75rem 1rem;
        }

        /* Alternating row colors */
        .stDataFrame tbody tr:nth-child(even) {
            background-color: #1a1f2e !important;
        }

        .stDataFrame tbody tr:nth-child(even):hover {
            background-color: #374151 !important;
        }

        /* ========================================
           METRICS - Card Style
           ======================================== */

        .stMetric {
            background-color: #1f2937;
            padding: 1.25rem;
            border-radius: 0.75rem;
            border: 1px solid #374151;
        }

        .stMetric label {
            color: #9ca3af !important;
            font-size: 0.875rem;
            font-weight: 500;
        }

        .stMetric [data-testid="stMetricValue"] {
            color: #fafafa !important;
            font-size: 1.875rem;
            font-weight: 700;
        }

        .stMetric [data-testid="stMetricDelta"] {
            font-size: 0.875rem;
        }

        /* ========================================
           ALERTS - Info/Warning/Success/Error
           ======================================== */

        .stAlert {
            background-color: #1f2937;
            border-radius: 0.5rem;
            padding: 1rem;
            border-left-width: 4px;
        }

        .stAlert[data-baseweb="notification"][kind="info"] {
            border-left-color: #3b82f6;
            background-color: rgba(59, 130, 246, 0.1);
        }

        .stAlert[data-baseweb="notification"][kind="success"] {
            border-left-color: #10b981;
            background-color: rgba(16, 185, 129, 0.1);
        }

        .stAlert[data-baseweb="notification"][kind="warning"] {
            border-left-color: #f59e0b;
            background-color: rgba(245, 158, 11, 0.1);
        }

        .stAlert[data-baseweb="notification"][kind="error"] {
            border-left-color: #ef4444;
            background-color: rgba(239, 68, 68, 0.1);
        }

        /* ========================================
           EXPANDERS - Collapsible Sections
           ======================================== */

        .stExpander {
            background-color: #1f2937;
            border: 1px solid #374151;
            border-radius: 0.5rem;
            margin-bottom: 0.5rem;
        }

        .stExpander summary {
            color: #fafafa;
            font-weight: 500;
            padding: 0.75rem 1rem;
        }

        .stExpander summary:hover {
            background-color: #374151;
            border-radius: 0.5rem;
        }

        .stExpander > div {
            padding: 1rem;
        }

        /* ========================================
           TABS - Clean & Modern
           ======================================== */

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
            background-color: transparent;
        }

        .stTabs [data-baseweb="tab"] {
            color: #9ca3af;
            background-color: #1f2937;
            border-radius: 0.5rem 0.5rem 0 0;
            padding: 0.75rem 1.5rem;
            border: 1px solid #374151;
            border-bottom: none;
            font-weight: 500;
        }

        .stTabs [data-baseweb="tab"]:hover {
            color: #fafafa;
            background-color: #374151;
        }

        .stTabs [aria-selected="true"] {
            background-color: #3b82f6 !important;
            color: #fafafa !important;
            border-color: #3b82f6 !important;
        }

        .stTabs [data-baseweb="tab-panel"] {
            background-color: #1f2937;
            border: 1px solid #374151;
            border-radius: 0 0.5rem 0.5rem 0.5rem;
            padding: 1.5rem;
        }

        /* ========================================
           FORMS - Grouped Sections
           ======================================== */

        .stForm {
            background-color: #1f2937;
            border: 1px solid #374151;
            padding: 1.5rem;
            border-radius: 0.75rem;
        }

        /* ========================================
           SIDEBAR - Navigation
           ======================================== */

        section[data-testid="stSidebar"] {
            background-color: #1f2937;
            border-right: 1px solid #374151;
        }

        section[data-testid="stSidebar"] > div {
            background-color: #1f2937;
        }

        /* ========================================
           CODE BLOCKS & JSON
           ======================================== */

        .stCodeBlock {
            background-color: #1e1e1e !important;
            border-radius: 0.5rem;
            border: 1px solid #374151;
        }

        .stJson {
            background-color: #1e1e1e;
            border-radius: 0.5rem;
            border: 1px solid #374151;
        }

        /* ========================================
           PROGRESS & SPINNERS
           ======================================== */

        .stProgress > div > div {
            background-color: #3b82f6;
        }

        .stSpinner > div {
            border-color: #3b82f6;
        }

        /* ========================================
           FILE UPLOADER
           ======================================== */

        .stFileUploader {
            background-color: #1f2937;
            border: 2px dashed #374151;
            border-radius: 0.75rem;
            padding: 2rem;
        }

        .stFileUploader:hover {
            border-color: #3b82f6;
        }

        .stFileUploader label {
            color: #fafafa !important;
        }

        /* ========================================
           DIVIDERS
           ======================================== */

        hr {
            border-color: #374151;
            margin: 1.5rem 0;
        }

        </style>
        """, unsafe_allow_html=True)
    else:
        # Explicit light mode CSS for consistency
        st.markdown("""
        <style>
        /* ========================================
           FINTEL LIGHT MODE - Clean & Professional
           ======================================== */

        /* Reset any dark mode remnants */
        .stApp {
            background-color: #ffffff;
            color: #262730;
        }

        /* Ensure text readability */
        h1, h2, h3, h4, h5, h6 {
            color: #262730 !important;
        }

        p, span, div {
            color: #555555;
        }

        /* Links */
        a {
            color: #1f77b4;
            text-decoration: none;
        }

        a:hover {
            text-decoration: underline;
            color: #155a8a;
        }

        /* Buttons - consistent styling */
        .stButton button {
            border-radius: 0.5rem;
            transition: all 0.2s ease;
        }

        .stButton button:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        /* Forms */
        .stForm {
            border: 1px solid #e0e0e0;
            padding: 1.5rem;
            border-radius: 0.75rem;
            background-color: #fafafa;
        }

        /* Metrics */
        .stMetric {
            background-color: #f5f5f5;
            padding: 1.25rem;
            border-radius: 0.75rem;
            border: 1px solid #e0e0e0;
        }

        /* DataFrames */
        .stDataFrame {
            border-radius: 0.5rem;
            overflow: hidden;
        }

        /* Expanders */
        .stExpander {
            border: 1px solid #e0e0e0;
            border-radius: 0.5rem;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #f8f9fa;
        }

        </style>
        """, unsafe_allow_html=True)
