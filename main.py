# main.py
import asyncio
import time
from core.data_fetcher import fetch_all_prices
from core.analytics import run_analytics
from database.database_setup import initialize_db

# --- CONFIGURATION ---
RUN_INTERVAL_SECONDS = 30

# --- NEW HELPER FUNCTION ---
def live_countdown(duration_seconds: int):
    """
    Displays a live, overwriting countdown in the terminal for the specified duration.
    """
    for i in range(duration_seconds, 0, -1):
        # The \r moves the cursor to the beginning of the line.
        # The end="" prevents print from adding a new line.
        # Padding with spaces ensures the previous line is fully overwritten.
        print(f"Next run in {i} seconds...          \r", end="")
        time.sleep(1)
    # Print a blank line to clear the countdown text at the end
    print(" " * 40, end="\r")

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

        # --- Wait for the next run with a live countdown ---
        print(f"--- Pipeline run finished. ---")
        print("===========================================")
        live_countdown(RUN_INTERVAL_SECONDS) # <--- UPDATED CALL

        print("-" * 30)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\n👋 Application shutting down. Goodbye!")