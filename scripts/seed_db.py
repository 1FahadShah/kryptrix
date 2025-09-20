# scripts/seed_db.py

import sqlite3
import sys
import os
import random
# FIX: Use timezone-aware UTC objects
from datetime import datetime, timedelta, timezone
import requests # Use requests for simple, synchronous calls in a script

# Add project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import TOKENS, DB_PATH, BINANCE_API_URL
from database.database_setup import create_connection

# --- NEW HELPER FUNCTION TO GET LIVE PRICE ---
def get_current_price(symbol: str) -> float:
    """Fetches the current price for a symbol from Binance for seeding."""
    try:
        # Construct the correct binance_id (e.g., 'BTC' -> 'BTCUSDT')
        binance_id = f"{symbol}USDT"
        url = f"{BINANCE_API_URL}/ticker/price?symbol={binance_id}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return float(data['price'])
    except Exception as e:
        print(f"Warning: Could not fetch live price for {symbol} for seeding. Using a default. Error: {e}")
        return 65000 if symbol == 'BTC' else 3500 # Fallback to old defaults

# --- UPDATED SEEDING FUNCTION ---
def seed_historical_data(conn, token_id, symbol):
    """Generates fake historical price data for a given token for development purposes."""
    print(f"Seeding historical data for {symbol} (token_id {token_id})...")
    cursor = conn.cursor()

    count = cursor.execute("SELECT COUNT(*) FROM prices WHERE token_id = ?", (token_id,)).fetchone()[0]
    if count > 0:
        print(f"Historical data already exists for {symbol}. Skipping.")
        return

    # --- FIX: Use live price as the base ---
    base_price = get_current_price(symbol)
    print(f"Using live base price for {symbol}: ${base_price:,.2f}")

    # Create 50 fake data points for the last day
    for i in range(50):
        # FIX: Use datetime.now(timezone.utc)
        timestamp = (datetime.now(timezone.utc) - timedelta(minutes=i * 30)).isoformat()

        # Make the price variation a percentage of the base price
        price_variation = base_price * random.uniform(-0.01, 0.01) # +/- 1%
        price = base_price + price_variation

        volume = random.uniform(1_000_000_000, 5_000_000_000)

        cursor.execute(
            """INSERT INTO prices (token_id, source, timestamp, price_usd, volume_24h)
               VALUES (?, ?, ?, ?, ?)""",
            (token_id, 'Binance', timestamp, price, volume)
        )
    conn.commit()
    print(f"Successfully seeded 50 historical data points for {symbol}.")

# --- (The rest of the file, seed_tokens() and if __name__ == "__main__", remains unchanged) ---
def seed_tokens():
    """
    Populates the 'tokens' table and seeds initial historical data for each token.
    This script is idempotent.
    """
    conn = create_connection(DB_PATH)
    if not conn:
        print("Failed to connect to the database. Aborting.")
        return

    try:
        cursor = conn.cursor()
        print("Seeding tokens into the database...")

        for token in TOKENS:
            cursor.execute(
                "INSERT OR IGNORE INTO tokens (symbol, name, source) VALUES (?, ?, ?)",
                (token['symbol'], token['name'], 'config')
            )
            token_id = cursor.execute("SELECT id FROM tokens WHERE symbol = ?", (token['symbol'],)).fetchone()[0]
            seed_historical_data(conn, token_id, token['symbol'])

        conn.commit()
        print(f"\nSuccessfully seeded/verified {len(TOKENS)} tokens and their historical data.")

    except sqlite3.Error as e:
        print(f"Database error during seeding: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    # Add requests to your requirements.txt
    seed_tokens()