# main.py
import asyncio
import time
from core.data_fetcher import fetch_all_prices
from core.analytics import run_analytics
from database.database_setup import initialize_db

# --- CONFIGURATION ---
RUN_INTERVAL_SECONDS = 30

# --- NEW ASYNC HELPER FUNCTION ---
async def live_countdown(duration_seconds: int):
    """
    Displays a live, non-blocking countdown in the terminal.
    """
    for i in range(duration_seconds, 0, -1):
        print(f"Next run in {i} seconds...          \r", end="")
        try:
            # Non-blocking sleep
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            # Allows clean cancellation
            break
    print(" " * 40, end="\r")  # Clear the countdown line

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

        # --- Wait for the next run with a live async countdown ---
        print(f"--- Pipeline run finished. ---")
        print("===========================================")
        await live_countdown(RUN_INTERVAL_SECONDS)  # <--- ASYNC CALL

        print("-" * 30)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        # Instant shutdown now works
        print("\n👋 Application shutting down gracefully. Goodbye!")
