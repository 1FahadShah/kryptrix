# core/feature_simulator.py

import pandas as pd
import json
import sqlite3
import sys
import os

# Add project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import DB_PATH, SIMULATION_ELASTICITY_CONSTANT, SIMULATION_BASE_FEE_PERCENT

# --- DATABASE HELPERS ---
def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def insert_simulation_result(conn: sqlite3.Connection, token_id: int, result: dict):
    """Saves a simulation result to the database."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO simulations (token_id, scenario, baseline, simulated, delta, recommendation, raw_data)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        token_id,
        result['scenario_name'],
        result['baseline_revenue'],
        result['simulated_revenue'],
        result['delta'],
        result['recommendation'],
        json.dumps(result)
    ))
    conn.commit()

# --- SIMULATION LOGIC ---
def simulate_fee_change_impact(
    historical_volume_data: pd.Series,
    proposed_fee_change_percent: float
) -> dict:
    """
    Simulates the revenue impact of changing trading fees.

    Args:
        historical_volume_data: A pandas Series of 24h trading volumes.
        proposed_fee_change_percent: The proposed change in fees (e.g., 0.05 for a 0.05% increase).

    Returns:
        A dictionary containing the simulation results.
    """
    if historical_volume_data.empty:
        return {}

    # --- 1. Calculate Baseline Metrics ---
    avg_daily_volume = historical_volume_data.mean()
    baseline_fee = SIMULATION_BASE_FEE_PERCENT / 100
    baseline_revenue = avg_daily_volume * baseline_fee

    # --- 2. Model the Impact on Volume (Elasticity) ---
    percent_change_in_fee = proposed_fee_change_percent / SIMULATION_BASE_FEE_PERCENT
    percent_change_in_volume = -SIMULATION_ELASTICITY_CONSTANT * percent_change_in_fee
    simulated_volume = avg_daily_volume * (1 + percent_change_in_volume)

    # --- 3. Calculate Simulated Revenue ---
    new_fee_percent = SIMULATION_BASE_FEE_PERCENT + proposed_fee_change_percent
    simulated_fee = new_fee_percent / 100
    simulated_revenue = simulated_volume * simulated_fee

    # --- 4. Determine Delta and Recommendation ---
    delta = simulated_revenue - baseline_revenue
    if delta > 0:
        recommendation = f"Positive Impact: The proposed fee change is projected to increase revenue by ${delta:,.2f}."
    elif delta < 0:
        recommendation = f"Negative Impact: The proposed fee change is projected to decrease revenue by ${abs(delta):,.2f}."
    else:
        recommendation = "Neutral Impact: No significant revenue change projected."

    # --- FIX: Format the output for a clean display ---
    result = {
        "scenario_name": f"Fee Change from {SIMULATION_BASE_FEE_PERCENT:.3f}% to {new_fee_percent:.3f}%",
        "baseline_revenue": baseline_revenue,
        "simulated_revenue": simulated_revenue,
        "delta": delta,
        "recommendation": recommendation,
        "inputs": {
            "avg_daily_volume": avg_daily_volume,
            "proposed_fee_change_percent": proposed_fee_change_percent
        }
    }
    return result

# You could add other simulation functions here, e.g., simulate_latency_impact()

if __name__ == '__main__':
    # Example of how to run the simulator directly for testing
    print("--- Running Feature Simulator Test ---")
    conn = get_db_connection()
    # Fetching some sample volume data for BTC (token_id=1)
    df = pd.read_sql_query("SELECT volume_24h FROM prices WHERE token_id = 1", conn)

    if not df.empty:
        # Test a scenario: increasing the fee by 0.02%
        proposed_change = 0.02
        simulation_result = simulate_fee_change_impact(df['volume_24h'], proposed_change)

        if simulation_result:
            print(f"Scenario: {simulation_result['scenario_name']}")
            print(f"  Baseline Daily Revenue: ${simulation_result['baseline_revenue']:,.2f}")
            print(f"  Simulated Daily Revenue: ${simulation_result['simulated_revenue']:,.2f}")
            print(f"  Projected Delta: ${simulation_result['delta']:,.2f}")
            print(f"  Recommendation: {simulation_result['recommendation']}")

            # Example of saving the result
            # insert_simulation_result(conn, 1, simulation_result)
            # print("\nTest result saved to database.")
    else:
        print("Not enough data in the database to run a simulation test.")

    conn.close()