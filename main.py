# main.py
import asyncio
import time
from core.data_fetcher import fetch_all_prices
from core.analytics import run_analytics
from database.database_setup import initialize_db

# --- CONFIGURATION ---
# The interval in seconds to wait between each full run of the data pipeline.
# 60 seconds is a safe bet to stay under free API rate limits.
RUN_INTERVAL_SECONDS = 60

async def main_loop():
    """
    The main execution loop for the Kryptrix application.
    Initializes the database, then continuously fetches and analyzes data.
    """
    print("🚀 Kryptrix application starting up...")

    # 1. Ensure the database and tables are created on startup
    initialize_db()
    print("-" * 30)

    # 2. Start the continuous data processing loop
    while True:
        print(f"[{time.ctime()}] --- Starting new data pipeline run ---")

        # --- Stage 1: Fetch Data ---
        print("Fetching latest prices from all sources...")
        await fetch_all_prices()
        print("Data fetching complete.")

        # --- Stage 2: Run Analytics ---
        print("Running analytics engine...")
        run_analytics()
        print("Analytics engine run complete.")

        # --- Wait for the next run ---
        print(f"--- Pipeline run finished. Waiting for {RUN_INTERVAL_SECONDS} seconds... ---")
        print("-" * 30)
        time.sleep(RUN_INTERVAL_SECONDS)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\n👋 Application shutting down. Goodbye!")