# scripts/seed_db.py
import sqlite3
import sys
import os
import random
from datetime import datetime, timedelta

# Add project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import TOKENS, DB_PATH
from database.database_setup import create_connection

def seed_historical_data(conn, token_id, symbol):
    """Generates fake historical price data for a given token for development purposes."""
    print(f"Seeding historical data for {symbol} (token_id {token_id})...")
    cursor = conn.cursor()

    # Check if data already exists to avoid re-seeding
    count = cursor.execute("SELECT COUNT(*) FROM prices WHERE token_id = ?", (token_id,)).fetchone()[0]
    if count > 0:
        print(f"Historical data already exists for {symbol}. Skipping.")
        return

    base_price = 65000 if symbol == 'BTC' else 3500

    # Create 50 fake data points for the last day
    for i in range(50):
        timestamp = (datetime.utcnow() - timedelta(minutes=i * 30)).isoformat()
        price = base_price + random.uniform(-500, 500)
        volume = random.uniform(1_000_000_000, 5_000_000_000)

        cursor.execute(
            """INSERT INTO prices (token_id, source, timestamp, price_usd, volume_24h)
               VALUES (?, ?, ?, ?, ?)""",
            (token_id, 'Binance', timestamp, price, volume)
        )
    conn.commit()
    print(f"Successfully seeded 50 historical data points for {symbol}.")


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
            # Insert the token if it doesn't exist
            cursor.execute(
                "INSERT OR IGNORE INTO tokens (symbol, name, source) VALUES (?, ?, ?)",
                (token['symbol'], token['name'], 'config')
            )

            # Get the token's ID (whether it was just inserted or already existed)
            token_id = cursor.execute("SELECT id FROM tokens WHERE symbol = ?", (token['symbol'],)).fetchone()[0]

            # Seed historical data for this token
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
    seed_tokens()