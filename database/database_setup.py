# database/database_setup.py
import sqlite3
from sqlite3 import Error
import os

# Database configuration
DB_DIR = "database"
DB_PATH = os.path.join(DB_DIR, "kryptrix.db")


def create_connection(db_path=DB_PATH):
    """
    Create a database connection to SQLite and enable foreign key constraints.
    Ensures the database directory exists.
    """
    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON;")  # Enable foreign keys
        print(f"SQLite DB connected at {db_path}")
        return conn
    except Error as e:
        print(f"Error connecting to database: {e}")
        return None


def create_tables(conn):
    """
    Create all tables required for Kryptrix.
    """
    tables = {}

    try:
        cursor = conn.cursor()

        # Tokens table
        tables['tokens'] = """
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            name TEXT,
            source TEXT NOT NULL
        )
        """
        cursor.execute(tables['tokens'])

        # Prices table - CORRECTED
        tables['prices'] = """
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_id INTEGER NOT NULL,
            source TEXT NOT NULL,
            timestamp DATETIME DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            price_usd REAL,
            volume_24h REAL,
            raw_data TEXT,
            FOREIGN KEY(token_id) REFERENCES tokens(id) ON DELETE CASCADE
        )
        """
        cursor.execute(tables['prices'])
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_token_time ON prices(token_id, timestamp)")

        # Indicators table
        tables['indicators'] = """
        CREATE TABLE IF NOT EXISTS indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_id INTEGER NOT NULL,
            timestamp DATETIME DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            sma10 REAL,
            sma30 REAL,
            ema REAL,
            rsi14 REAL,
            vwap24h REAL,
            realized_vol REAL,
            raw_data TEXT,
            FOREIGN KEY(token_id) REFERENCES tokens(id) ON DELETE CASCADE
        )
        """
        cursor.execute(tables['indicators'])
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_indicators_token_time ON indicators(token_id, timestamp)")

        # Arbitrage table
        tables['arbitrage'] = """
        CREATE TABLE IF NOT EXISTS arbitrage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_id INTEGER NOT NULL,
            timestamp DATETIME DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            source_a TEXT,
            source_b TEXT,
            price_diff REAL,
            percent_diff REAL,
            raw_data TEXT,
            FOREIGN KEY(token_id) REFERENCES tokens(id) ON DELETE CASCADE
        )
        """
        cursor.execute(tables['arbitrage'])
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_arbitrage_token_time ON arbitrage(token_id, timestamp)")

        # Anomalies table
        tables['anomalies'] = """
        CREATE TABLE IF NOT EXISTS anomalies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_id INTEGER NOT NULL,
            timestamp DATETIME DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            anomaly_type TEXT,
            value REAL,
            description TEXT,
            raw_data TEXT,
            FOREIGN KEY(token_id) REFERENCES tokens(id) ON DELETE CASCADE
        )
        """
        cursor.execute(tables['anomalies'])
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_token_time ON anomalies(token_id, timestamp)")

        # API Health / Logs table
        tables['api_health'] = """
        CREATE TABLE IF NOT EXISTS api_health (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            timestamp DATETIME DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            status TEXT,
            response_time_ms REAL,
            error_message TEXT,
            raw_data TEXT
        )
        """
        cursor.execute(tables['api_health'])
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_health_source_time ON api_health(source, timestamp)")

        # Feature Simulations (A/B testing) table
        tables['simulations'] = """
        CREATE TABLE IF NOT EXISTS simulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_id INTEGER NOT NULL,
            timestamp DATETIME DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            scenario TEXT,
            baseline REAL,
            simulated REAL,
            delta REAL,
            recommendation TEXT,
            raw_data TEXT,
            FOREIGN KEY(token_id) REFERENCES tokens(id) ON DELETE CASCADE
        )
        """
        cursor.execute(tables['simulations'])
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_simulations_token_time ON simulations(token_id, timestamp)")

        # Stakeholder Requests table
        tables['stakeholder_requests'] = """
        CREATE TABLE IF NOT EXISTS stakeholder_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request TEXT NOT NULL,
            submitted_at DATETIME DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            processed INTEGER DEFAULT 0,
            response TEXT
        )
        """
        cursor.execute(tables['stakeholder_requests'])

        conn.commit()
        print("All tables created successfully.")

    except Error as e:
        print(f"Error creating tables: {e}")


def initialize_db():
    """
    Initialize the database: create connection and tables.
    """
    conn = create_connection()
    if conn:
        create_tables(conn)
        conn.close()
        print("Database setup complete.")


if __name__ == "__main__":
    initialize_db()