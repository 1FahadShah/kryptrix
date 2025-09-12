# core/analytics.py
import pandas as pd
import ta # <--- NEW LIBRARY
import sqlite3
import json
import sys
import os
from datetime import datetime, timezone, timedelta

# Add project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import DB_PATH, TOKENS

# --- CONFIGURATION ---
DATA_LOOKBACK_HOURS = 72
ARBITRAGE_THRESHOLD = 0.01  # 1%

# --- DATABASE HELPERS ---
def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_token_id(conn, symbol):
    """Fetches the ID for a given token symbol."""
    return conn.execute("SELECT id FROM tokens WHERE symbol = ?", (symbol,)).fetchone()['id']

def insert_indicators(conn, token_id, indicators):
    """Inserts the latest calculated indicators into the database."""
    cursor = conn.cursor()
    # Storing None for vwap and realized_vol for now
    cursor.execute("""
        INSERT INTO indicators (token_id, sma10, sma30, ema, rsi14, vwap24h, realized_vol, raw_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        token_id,
        indicators.get('SMA_10'),
        indicators.get('SMA_30'),
        indicators.get('EMA_14'),
        indicators.get('RSI_14'),
        None, # VWAP temporarily removed
        None, # Realized Volatility temporarily removed
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

# --- ANALYTICS FUNCTIONS ---
def calculate_technical_indicators(df: pd.DataFrame) -> dict:
    """Calculates a set of technical indicators using the 'ta' library."""
    if df.empty or len(df) < 30:
        print("Warning: Not enough data points to calculate all indicators.")
        return {}

    # Use the 'ta' library to calculate indicators
    # It automatically finds the 'close' column
    df['SMA_10'] = ta.trend.sma_indicator(df['close'], window=10)
    df['SMA_30'] = ta.trend.sma_indicator(df['close'], window=30)
    df['EMA_14'] = ta.trend.ema_indicator(df['close'], window=14)
    df['RSI_14'] = ta.momentum.rsi(df['close'], window=14)

    # Get the most recent indicator values
    latest_indicators = df.iloc[-1].to_dict()

    # Clean up NaN values for JSON serialization
    return {k: v for k, v in latest_indicators.items() if pd.notna(v)}

def detect_arbitrage(df: pd.DataFrame) -> list:
    """Detects arbitrage opportunities from the latest prices across different sources."""
    opportunities = []
    latest = df.sort_values('timestamp').drop_duplicates('source', keep='last')

    if len(latest) < 2:
        return []

    import itertools
    for (idx_a, row_a), (idx_b, row_b) in itertools.combinations(latest.iterrows(), 2):
        price_a = row_a['price_usd']
        price_b = row_b['price_usd']

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

# --- MAIN RUNNER ---
def run_analytics():
    """Main function to run all analytics for all configured tokens."""
    print("Starting analytics engine...")
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

            # Prepare DataFrame: 'ta' needs a 'close' column
            df.rename(columns={'price_usd': 'close'}, inplace=True)

            indicators = calculate_technical_indicators(df.copy())
            if indicators:
                insert_indicators(conn, token_id, indicators)
                print(f"Successfully calculated and stored indicators for {symbol}.")

            # Rename back to original for arbitrage detection
            df.rename(columns={'close': 'price_usd'}, inplace=True)
            arbitrage_opps = detect_arbitrage(df)
            if arbitrage_opps:
                for opp in arbitrage_opps:
                    insert_arbitrage(conn, token_id, opp)
                print(f"Found and stored {len(arbitrage_opps)} arbitrage opportunity for {symbol}.")

        except Exception as e:
            print(f"An error occurred while processing {symbol}: {e}")

    conn.close()
    print("\nAnalytics engine run complete.")

if __name__ == "__main__":
    run_analytics()