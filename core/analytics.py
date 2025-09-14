# core/analytics.py
import pandas as pd
import ta  # <--- NEW LIBRARY
import sqlite3
import json
import sys
import os
from datetime import datetime, timezone, timedelta
import numpy as np

# Add project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import DB_PATH, TOKENS, SOURCES # <-- IMPORT SOURCES

# --- CONFIGURATION ---
DATA_LOOKBACK_HOURS = 72
ARBITRAGE_THRESHOLD = 0.001  # 0.1%

# --- NEW: Anomaly Detection Configuration ---
ANOMALY_ZSCORE_WINDOW = 24  # Use the last 24 data points for Z-score calculation
ANOMALY_ZSCORE_THRESHOLD = 3.0  # Z-score above this is a volume spike
ANOMALY_PRICE_JUMP_THRESHOLD = 0.05  # 5% price change in one period is a price jump

# --- DATABASE HELPERS ---
def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_token_id(conn, symbol):
    """Fetches the ID for a given token symbol."""
    return conn.execute("SELECT id FROM tokens WHERE symbol = ?", (symbol,)).fetchone()['id']

def insert_indicators(conn, token_id, indicators, timestamp):
    """Inserts the latest calculated indicators into the database with the correct timestamp."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO indicators (token_id, timestamp, sma10, sma30, ema, rsi14, vwap24h, realized_vol, raw_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        token_id,
        timestamp,
        indicators.get('SMA_10'),
        indicators.get('SMA_30'),
        indicators.get('EMA_14'),
        indicators.get('RSI_14'),
        None,  # VWAP temporarily removed
        None,  # Realized Volatility temporarily removed
        json.dumps(indicators)
    ))
    conn.commit()

def insert_arbitrage(conn, token_id, opp):
    """Inserts a detected arbitrage opportunity into the database."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO arbitrage (token_id, source_a, source_b, price_diff, percent_diff, raw_data)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        token_id,
        opp['source_a'],
        opp['source_b'],
        opp['price_diff'],
        opp['percent_diff'],
        json.dumps(opp)
    ))
    conn.commit()

# --- NEW: Anomaly Insertion Helper ---
def insert_anomaly(conn, token_id, anomaly):
    """Inserts a detected anomaly into the database."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO anomalies (token_id, anomaly_type, value, description, raw_data)
        VALUES (?, ?, ?, ?, ?)
    """, (
        token_id,
        anomaly['anomaly_type'],
        anomaly['value'],
        anomaly['description'],
        json.dumps(anomaly)
    ))
    conn.commit()

# --- ANALYTICS FUNCTIONS ---
def calculate_technical_indicators(df: pd.DataFrame) -> tuple:
    """Calculates a set of technical indicators and returns them with the latest timestamp."""
    if df.empty or len(df) < 30:
        print("Warning: Not enough data points to calculate all indicators.")
        return {}, None

    df['SMA_10'] = ta.trend.sma_indicator(df['close'], window=10)
    df['SMA_30'] = ta.trend.sma_indicator(df['close'], window=30)
    df['EMA_14'] = ta.trend.ema_indicator(df['close'], window=14)
    df['RSI_14'] = ta.momentum.rsi(df['close'], window=14)

    latest_row = df.iloc[-1]
    latest_indicators = latest_row.to_dict()
    latest_timestamp = latest_row['timestamp']

    # Clean up the indicators dict
    indicators_only = {k: v for k, v in latest_indicators.items() if pd.notna(v) and k not in ['timestamp', 'close']}

    return indicators_only, latest_timestamp

def detect_arbitrage(df: pd.DataFrame) -> list:
    """Detects arbitrage opportunities from the latest prices across different sources."""
    opportunities = []

    # --- FIX: Filter for executable exchanges ONLY ---
    exchange_names = [name for name, props in SOURCES.items() if props.get('is_exchange', False)]
    df_exchanges = df[df['source'].isin(exchange_names)]

    latest = df_exchanges.sort_values('timestamp').drop_duplicates('source', keep='last')

    if len(latest) < 2:
        return []

    import itertools
    for (idx_a, row_a), (idx_b, row_b) in itertools.combinations(latest.iterrows(), 2):
        price_a = row_a['price_usd']
        price_b = row_b['price_usd']

        if price_a is None or price_b is None or price_a == 0 or price_b == 0:
            continue

        price_diff = abs(price_a - price_b)
        percent_diff = price_diff / min(price_a, price_b)

        if percent_diff >= ARBITRAGE_THRESHOLD:
            if price_a < price_b:
                buy_source, sell_source = row_a['source'], row_b['source']
                buy_price, sell_price = price_a, price_b
            else:
                buy_source, sell_source = row_b['source'], row_a['source']
                buy_price, sell_price = price_b, price_a

            opportunities.append({
                "source_a": f"Buy at {buy_source}",
                "source_b": f"Sell at {sell_source}",
                "price_diff": sell_price - buy_price,
                "percent_diff": percent_diff * 100,
                "buy_price": buy_price,
                "sell_price": sell_price,
            })
    return opportunities

# --- NEW: Anomaly Detection Function ---
def detect_anomalies(df: pd.DataFrame) -> list:
    """Detects volume spikes and price jumps from time-series data."""
    anomalies = []
    df = df.sort_values('timestamp').reset_index(drop=True)

    if df.empty:
        return []

    # Volume Spike Detection (Z-score)
    if 'volume_24h' in df.columns and len(df) >= ANOMALY_ZSCORE_WINDOW:
        rolling_window = df['volume_24h'].iloc[-ANOMALY_ZSCORE_WINDOW:]
        mean = rolling_window.mean()
        std = rolling_window.std()

        if std > 0:
            latest_volume = rolling_window.iloc[-1]
            z_score = (latest_volume - mean) / std
            if abs(z_score) >= ANOMALY_ZSCORE_THRESHOLD:
                anomalies.append({
                    "anomaly_type": "Volume Spike",
                    "value": z_score,
                    "description": f"Volume Z-score of {z_score:.2f} exceeds threshold ({ANOMALY_ZSCORE_THRESHOLD}). Current Volume: {latest_volume:,.2f}",
                })

    # Price Jump Detection (% change)
    if 'close' in df.columns and len(df) >= 2:
        df['price_pct_change'] = df['close'].pct_change()
        latest_change = df['price_pct_change'].iloc[-1]

        if pd.notna(latest_change) and abs(latest_change) >= ANOMALY_PRICE_JUMP_THRESHOLD:
            anomalies.append({
                "anomaly_type": "Price Jump",
                "value": latest_change * 100,
                "description": f"Price changed by {latest_change:.2%}, exceeding threshold of {ANOMALY_PRICE_JUMP_THRESHOLD:.2%}.",
            })

    return anomalies

# --- MAIN RUNNER ---
def run_analytics():
    """Main function to run all analytics for all configured tokens."""
    print("Starting analytics engine...")
    conn = None
    try:
        conn = get_db_connection()
        for token_config in TOKENS:
            symbol = token_config['symbol']
            print(f"--- Processing analytics for {symbol} ---")
            try:
                token_id = get_token_id(conn, symbol)
                lookback_time = (datetime.now(timezone.utc) - timedelta(hours=DATA_LOOKBACK_HOURS)).isoformat()
                query = "SELECT * FROM prices WHERE token_id = ? AND timestamp >= ? ORDER BY timestamp ASC"
                df = pd.read_sql_query(query, conn, params=(token_id, lookback_time))

                if df.empty:
                    print(f"No recent price data found for {symbol}. Skipping.")
                    continue

                # Keep a copy of the original dataframe before renaming columns
                df_original = df.copy()

                # Prepare DataFrame for TA library: 'ta' needs a 'close' column
                df.rename(columns={'price_usd': 'close'}, inplace=True)

                # Technical Indicators
                indicators, latest_timestamp = calculate_technical_indicators(df.copy())
                if indicators:
                    insert_indicators(conn, token_id, indicators, latest_timestamp)
                    print(f"Successfully calculated and stored indicators for {symbol}.")

                # Arbitrage (use the original dataframe with 'price_usd')
                arbitrage_opps = detect_arbitrage(df_original)
                if arbitrage_opps:
                    for opp in arbitrage_opps:
                        insert_arbitrage(conn, token_id, opp)
                    print(f"Found and stored {len(arbitrage_opps)} arbitrage opportunities for {symbol}.")

                # Anomalies (use the original dataframe and the one with 'close')
                anomalies_found = detect_anomalies(df.copy())
                if anomalies_found:
                    for anomaly in anomalies_found:
                        insert_anomaly(conn, token_id, anomaly)
                    print(f"Found and stored {len(anomalies_found)} anomalies for {symbol}.")

            except Exception as e:
                print(f"An error occurred while processing {symbol}: {e}")
    finally:
        if conn:
            conn.close()
        print("\nAnalytics engine run complete.")

if __name__ == "__main__":
    run_analytics()