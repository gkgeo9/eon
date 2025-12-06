#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fintel Streamlit Web Application

Entry point for the Streamlit-based frontend.
Run with: streamlit run streamlit_app.py
"""

import streamlit as st
from src.fintel.ui.app import main

# Configure page
st.set_page_config(
    page_title="Fintel - Financial Intelligence Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

if __name__ == "__main__":
    main()
