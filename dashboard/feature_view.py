# dashboard/feature_view.py

import streamlit as st
import pandas as pd
import sqlite3
import sys
import os

# Add project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.feature_simulator import simulate_fee_change_impact
from config import DB_PATH, TOKENS

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)

@st.cache_data(ttl=300) # Cache for 5 minutes
def fetch_volume_data(token_symbol: str):
    """Fetches historical 24h volume data for a specific token."""
    conn = get_db_connection()

    # Get token_id from symbol
    token_id_query = "SELECT id FROM tokens WHERE symbol = ?"
    token_id_df = pd.read_sql_query(token_id_query, conn, params=(token_symbol,))
    if token_id_df.empty:
        conn.close()
        return pd.Series(dtype='float64') # Return empty series if token not found
    token_id = token_id_df.iloc[0, 0]

    # Fetch volume data
    volume_query = "SELECT volume_24h FROM prices WHERE token_id = ?"
    df_volume = pd.read_sql_query(volume_query, conn, params=(token_id,))

    conn.close()
    return df_volume['volume_24h']

def render_feature_view():
    """Renders the Feature Simulator view."""
    st.subheader("Simulate Business Decisions")

    st.info("""
    **How does this work?** This tool uses a simple price elasticity model to project how a change
    in trading fees might impact trading volume and, consequently, overall revenue.
    """)

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Simulation Parameters")
        token_symbols = [token['symbol'] for token in TOKENS]
        selected_token = st.selectbox(
            "Select a token to base the simulation on:",
            token_symbols
        )

        fee_change = st.slider(
            "Proposed Fee Change (%)",
            min_value=-0.05,
            max_value=0.05,
            value=0.01, # Default value
            step=0.005,
            format="%.3f%%"
        )

        run_button = st.button("Run Simulation")

    with col2:
        st.subheader("Simulation Results")
        if run_button:
            with st.spinner("Running simulation..."):
                volume_data = fetch_volume_data(selected_token)

                if volume_data.empty:
                    st.error(f"Not enough historical volume data for {selected_token} to run a simulation.")
                    return

                result = simulate_fee_change_impact(volume_data, fee_change)

                if result:
                    res_col1, res_col2, res_col3 = st.columns(3)
                    with res_col1:
                        st.metric(
                            label="Baseline Daily Revenue",
                            value=f"${result['baseline_revenue']:,.2f}"
                        )
                    with res_col2:
                        st.metric(
                            label="Simulated Daily Revenue",
                            value=f"${result['simulated_revenue']:,.2f}",
                            delta=f"${result['delta']:,.2f}"
                        )
                    with res_col3:
                         st.metric(
                            label="Scenario",
                            value=result['scenario_name']
                        )
                    st.success(result['recommendation'])
                else:
                    st.error("Failed to compute simulation results.")