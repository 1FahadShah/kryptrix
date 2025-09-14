# dashboard/trading_view.py (Final Version with utc=True Fix)

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

@st.cache_data(ttl=60)
def fetch_trading_data(token_symbol: str):
    """Fetches data and ensures consistent dtypes before merging."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get token_id from symbol
        cursor.execute("SELECT id FROM tokens WHERE symbol = ?", (token_symbol,))
        token_result = cursor.fetchone()
        if not token_result:
            return pd.DataFrame()
        token_id = token_result[0]

        # Fetch prices and indicators as raw data first
        prices_data = cursor.execute("SELECT timestamp, price_usd FROM prices WHERE token_id = ? AND UPPER(source) = 'BINANCE' ORDER BY timestamp", (token_id,)).fetchall()
        indicators_data = cursor.execute("SELECT timestamp, sma10, sma30, ema FROM indicators WHERE token_id = ? ORDER BY timestamp", (token_id,)).fetchall()

        df_prices = pd.DataFrame(prices_data, columns=['timestamp', 'price_usd'])
        df_indicators = pd.DataFrame(indicators_data, columns=['timestamp', 'sma10', 'sma30', 'ema'])

        if df_prices.empty:
            return pd.DataFrame()

        # --- FIX: Use utc=True to robustly parse mixed timezone formats ---
        df_prices['timestamp'] = pd.to_datetime(df_prices['timestamp'], format='mixed', utc=True)

        if not df_indicators.empty:
            # --- FIX: Use utc=True here as well for consistency ---
            df_indicators['timestamp'] = pd.to_datetime(df_indicators['timestamp'], utc=True)
            df_merged = pd.merge(df_prices, df_indicators, on='timestamp', how='left')
        else:
            df_merged = df_prices
            df_merged['sma10'] = None
            df_merged['sma30'] = None
            df_merged['ema'] = None

        return df_merged

    finally:
        conn.close()

def render_trading_view():
    """Renders the Trading Analytics view."""
    st.subheader("Token Performance Analysis")

    token_symbols = [token['symbol'] for token in TOKENS]
    selected_token = st.selectbox("Select a Token to Analyze", token_symbols)

    if selected_token:
        try:
            with st.spinner(f"Loading data for {selected_token}..."):
                df = fetch_trading_data(selected_token)

            if df.empty or df['price_usd'].isnull().all():
                st.warning("Not enough historical price data available. Please run the seeder or data fetcher script.")
                return

            if df['sma10'].isnull().all():
                 st.info("Indicator data not yet calculated. Run the analytics engine (`core/analytics.py`) to see SMA/EMA lines.")

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df['price_usd'], mode='lines', name='Price (USD)', line=dict(color='blue', width=2)))

            if not df['sma10'].isnull().all():
                fig.add_trace(go.Scatter(x=df['timestamp'], y=df['sma10'], mode='lines', name='SMA 10', line=dict(color='orange', width=1, dash='dot')))
            if not df['sma30'].isnull().all():
                fig.add_trace(go.Scatter(x=df['timestamp'], y=df['sma30'], mode='lines', name='SMA 30', line=dict(color='green', width=1, dash='dot')))
            if not df['ema'].isnull().all():
                fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ema'], mode='lines', name='EMA 14', line=dict(color='red', width=1, dash='dash')))

            fig.update_layout(title=f'{selected_token}/USD Price and Technical Indicators', xaxis_title='Date', yaxis_title='Price (USD)', legend_title='Legend', template='plotly_white')
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Historical Data")
            st.dataframe(df.tail(20).sort_values('timestamp', ascending=False), hide_index=True)

        except Exception as e:
            st.error(f"An error occurred while loading data for {selected_token}: {e}")