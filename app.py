# app.py (Merged for Hugging Face Deployment)

import streamlit as st
import asyncio
import threading
import time
import os
import sys

# --- Add project root to path to find other modules ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# --- Imports from your project ---
from dashboard import layout, kpi_view, trading_view, feature_view, stakeholder_view
from core.data_fetcher import fetch_all_prices
from core.analytics import run_analytics
from database.database_setup import initialize_db
from scripts.seed_db import seed_tokens # Use the seeder function directly

# --- Page Configuration ---
st.set_page_config(
    page_title="Kryptrix Analytics",
    page_icon="📈",
    layout="wide"
)

# --- 1. BACKGROUND DATA PIPELINE LOGIC (from main.py) ---
# This is your asynchronous data processing loop.
async def data_pipeline_loop():
    """Continuously fetches and analyzes data in an async loop."""
    RUN_INTERVAL_SECONDS = 60 # Set a reasonable interval for a deployed app

    while True:
        print(f"[{time.ctime()}] --- BACKGROUND: Starting new data pipeline run ---")
        try:
            # Stage 1: Fetch Data
            print("BACKGROUND: Fetching latest prices...")
            await fetch_all_prices()
            print("BACKGROUND: Data fetching complete.")

            # Stage 2: Run Analytics
            print("BACKGROUND: Running analytics engine...")
            run_analytics()
            print("BACKGROUND: Analytics engine run complete.")

        except Exception as e:
            print(f"BACKGROUND ERROR: An error occurred in the pipeline: {e}")

        # Wait for the next run
        print(f"BACKGROUND: Pipeline run finished. Waiting for {RUN_INTERVAL_SECONDS} seconds.")
        await asyncio.sleep(RUN_INTERVAL_SECONDS)

# This function is the target for our background thread.
# It sets up and runs the asyncio event loop for the data pipeline.
def run_background_pipeline():
    """Runs the async data pipeline loop in a separate thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(data_pipeline_loop())

# --- 2. ONE-TIME SETUP LOGIC (from run.py) ---
# We use Streamlit's session state to ensure this runs only ONCE.
def initial_setup():
    """
    Performs database initialization and seeding.
    This function is designed to run only once per app session.
    """
    print("--- Performing initial setup: DB and Seeding ---")
    initialize_db()
    seed_tokens() # This will seed tokens and initial historical data
    print("--- Initial setup complete ---")


# --- 3. STREAMLIT UI LOGIC (your original app.py) ---
def run_streamlit_app():
    """Main function to render the Streamlit UI."""
    st.sidebar.title("Kryptrix Navigation")
    page = layout.setup_sidebar()

    if page == "KPI Dashboard":
        st.title("📈 KPI Dashboard")
        kpi_view.render_kpi_view()
    elif page == "Trading Analytics":
        st.title("💹 Trading Analytics")
        trading_view.render_trading_view()
    elif page == "Feature Simulator":
        st.title("🔬 Feature Simulator")
        feature_view.render_feature_view()
    elif page == "Stakeholder Reports":
        st.title("📄 Stakeholder Reports")
        stakeholder_view.render_stakeholder_view()


# --- MAIN EXECUTION BLOCK ---
if __name__ == "__main__":
    # Use session state to run setup and background thread only once
    if 'initialized' not in st.session_state:
        # Perform the one-time database setup and seeding
        initial_setup()

        # Start the background data pipeline in a separate thread
        print("--- Starting background data pipeline thread ---")
        pipeline_thread = threading.Thread(target=run_background_pipeline, daemon=True)
        pipeline_thread.start()
        print("--- Background thread started ---")

        # Set a flag in session state to indicate initialization is done
        st.session_state['initialized'] = True

    # Run the main Streamlit application UI
    run_streamlit_app()