# dashboard/layout.py

import streamlit as st

def setup_sidebar():
    """
    Sets up the sidebar navigation for the Streamlit app.
    Returns the selected page.
    """
    page = st.sidebar.radio(
        "Select a Page",
        ("KPI Dashboard", "Trading Analytics", "Feature Simulator", "Stakeholder Reports")
    )
    return page