# dashboard/kpi_view.py

import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime, timedelta, timezone
import os
import sys

# Add project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import DB_PATH

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)

@st.cache_data(ttl=60) # Cache data for 60 seconds
def fetch_kpi_data():
    """Fetches all data required for the KPI dashboard from the database."""
    conn = get_db_connection()

    # 1. Fetch latest prices for all tokens
    latest_prices_query = """
    SELECT t.symbol, p.price_usd
    FROM prices p
    JOIN tokens t ON p.token_id = t.id
    WHERE p.id IN (
        SELECT MAX(id)
        FROM prices
        GROUP BY token_id, source
    ) AND p.source = 'Binance'
    """
    df_prices = pd.read_sql_query(latest_prices_query, conn)

    # 2. Fetch recent anomaly and arbitrage counts
    time_24h_ago = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    anomaly_count = pd.read_sql_query("SELECT COUNT(*) FROM anomalies WHERE timestamp >= ?", conn, params=(time_24h_ago,)).iloc[0, 0]
    arbitrage_count = pd.read_sql_query("SELECT COUNT(*) FROM arbitrage WHERE timestamp >= ?", conn, params=(time_24h_ago,)).iloc[0, 0]

    # 3. Fetch data for API health chart
    df_api_health = pd.read_sql_query("SELECT source, status, timestamp FROM api_health WHERE timestamp >= ?", conn, params=(time_24h_ago,))

    # 4. Fetch recent anomalies for table display
    df_recent_anomalies = pd.read_sql_query("SELECT timestamp, anomaly_type, description FROM anomalies ORDER BY timestamp DESC LIMIT 5", conn)

    conn.close()

    return {
        "prices": df_prices,
        "anomaly_count_24h": anomaly_count,
        "arbitrage_count_24h": arbitrage_count,
        "api_health": df_api_health,
        "recent_anomalies": df_recent_anomalies
    }

def render_kpi_view():
    """Renders the KPI Dashboard view."""
    try:
        with st.spinner("Loading dashboard data..."):
            data = fetch_kpi_data()

        # --- KPI Metrics Section ---
        st.subheader("Live Market Snapshot")
        cols = st.columns(len(data['prices']) + 2)
        for i, row in data['prices'].iterrows():
            with cols[i]:
                st.metric(label=f"{row['symbol']}/USD", value=f"${row['price_usd']:,.2f}")
        with cols[len(data['prices'])]:
            st.metric(label="Anomalies (24h)", value=data['anomaly_count_24h'])
        with cols[len(data['prices']) + 1]:
            st.metric(label="Arbitrage Ops (24h)", value=data['arbitrage_count_24h'])

        st.markdown("---")

        # --- FIX: Main sections now stack vertically for mobile friendliness ---
        st.subheader("API Health Status (Last 24h)")
        if not data['api_health'].empty:
            health_summary = data['api_health'].groupby(['source', 'status']).size().reset_index(name='count')
            fig = px.bar(
                health_summary, x='source', y='count', color='status',
                title='API Fetch Success vs. Errors',
                labels={'count': 'Number of Requests', 'source': 'API Source'},
                color_discrete_map={'success': 'green', 'error': 'red'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No API health data available for the last 24 hours.")

        st.subheader("Recent Anomalies")
        if not data['recent_anomalies'].empty:
            st.dataframe(
                data['recent_anomalies'],
                hide_index=True, use_container_width=True,
                column_config={
                    "timestamp": st.column_config.DatetimeColumn("Timestamp", format="YYYY-MM-DD HH:mm:ss"),
                    "anomaly_type": st.column_config.TextColumn("Type"),
                    "description": st.column_config.TextColumn("Description", width="large")
                }
            )
        else:
            st.info("No recent anomalies detected.")

    except Exception as e:
        st.error(f"An error occurred while loading the dashboard: {e}")