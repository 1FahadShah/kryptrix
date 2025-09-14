# dashboard/trading_view.py

import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import os
import sys

# Add project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import DB_PATH, TOKENS

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)

@st.cache_data(ttl=60) # Cache data for 60 seconds
def fetch_trading_data(token_symbol: str):
    """Fetches historical price and indicator data for a specific token."""
    conn = get_db_connection()

    # Get token_id from symbol
    token_id_query = "SELECT id FROM tokens WHERE symbol = ?"
    token_id = pd.read_sql_query(token_id_query, conn, params=(token_symbol,)).iloc[0, 0]

    # Fetch prices and indicators
    prices_query = """
    SELECT timestamp, price_usd
    FROM prices
    WHERE token_id = ? AND source = 'Binance'
    ORDER BY timestamp
    """
    df_prices = pd.read_sql_query(prices_query, conn, params=(token_id,))
    df_prices['timestamp'] = pd.to_datetime(df_prices['timestamp'])

    indicators_query = """
    SELECT timestamp, sma10, sma30, ema
    FROM indicators
    WHERE token_id = ?
    ORDER BY timestamp
    """
    df_indicators = pd.read_sql_query(indicators_query, conn, params=(token_id,))
    df_indicators['timestamp'] = pd.to_datetime(df_indicators['timestamp'])

    # Merge the dataframes based on the timestamp
    df_merged = pd.merge(df_prices, df_indicators, on='timestamp', how='left')

    conn.close()
    return df_merged

def render_trading_view():
    """Renders the Trading Analytics view."""

    st.subheader("Token Performance Analysis")

    # --- Token Selection Dropdown ---
    token_symbols = [token['symbol'] for token in TOKENS]
    selected_token = st.selectbox("Select a Token to Analyze", token_symbols)

    if selected_token:
        try:
            with st.spinner(f"Loading data for {selected_token}..."):
                df = fetch_trading_data(selected_token)

            if df.empty:
                st.warning("Not enough historical data available to generate a chart.")
                return

            # --- Interactive Chart ---
            fig = go.Figure()

            # Price Line
            fig.add_trace(go.Scatter(
                x=df['timestamp'], y=df['price_usd'],
                mode='lines', name='Price (USD)',
                line=dict(color='blue', width=2)
            ))

            # SMA10 Line
            fig.add_trace(go.Scatter(
                x=df['timestamp'], y=df['sma10'],
                mode='lines', name='SMA 10',
                line=dict(color='orange', width=1, dash='dot')
            ))

            # SMA30 Line
            fig.add_trace(go.Scatter(
                x=df['timestamp'], y=df['sma30'],
                mode='lines', name='SMA 30',
                line=dict(color='green', width=1, dash='dot')
            ))

            # EMA Line
            fig.add_trace(go.Scatter(
                x=df['timestamp'], y=df['ema'],
                mode='lines', name='EMA 14',
                line=dict(color='red', width=1, dash='dash')
            ))

            fig.update_layout(
                title=f'{selected_token}/USD Price and Technical Indicators',
                xaxis_title='Date',
                yaxis_title='Price (USD)',
                legend_title='Legend',
                template='plotly_white'
            )

            st.plotly_chart(fig, use_container_width=True)

            # --- Data Table ---
            st.subheader("Historical Data")
            st.dataframe(df.tail(20).sort_values('timestamp', ascending=False), hide_index=True)

        except Exception as e:
            st.error(f"An error occurred while loading data for {selected_token}: {e}")