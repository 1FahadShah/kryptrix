# scripts/seed_db.py
import sqlite3
import sys
import os

# Add project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import TOKENS, DB_PATH
from database.database_setup import create_connection

def seed_tokens():
    """
    Populates the 'tokens' table with the initial set of cryptocurrencies
    from the config file. This script is idempotent, meaning it can be
    run multiple times without creating duplicate entries.
    """
    conn = create_connection(DB_PATH)
    if not conn:
        print("Failed to connect to the database. Aborting.")
        return

    try:
        cursor = conn.cursor()
        print("Seeding tokens into the database...")

        for token in TOKENS:
            # Using INSERT OR IGNORE to prevent errors if the token already exists
            cursor.execute(
                "INSERT OR IGNORE INTO tokens (symbol, name, source) VALUES (?, ?, ?)",
                (token['symbol'], token['name'], 'config')
            )

        conn.commit()
        print(f"Successfully seeded/verified {len(TOKENS)} tokens.")

    except sqlite3.Error as e:
        print(f"Database error during seeding: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    seed_tokens()