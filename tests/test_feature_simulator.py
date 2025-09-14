# tests/test_feature_simulator.py

import pandas as pd
import numpy as np
import sys
import os

# Add project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.feature_simulator import simulate_fee_change_impact
from config import SIMULATION_BASE_FEE_PERCENT, SIMULATION_ELASTICITY_CONSTANT

def test_simulate_fee_change_impact():
    """
    Tests the fee simulation with a predictable dataset.
    """
    # 1. Arrange: Create sample volume data and a proposed fee change
    sample_volume = pd.Series([1000, 1000, 1000, 1000]) # Consistent volume for easy math
    proposed_change = 0.02 # A 0.02% increase

    # 2. Act: Run the simulation
    result = simulate_fee_change_impact(sample_volume, proposed_change)

    # 3. Assert: Manually calculate the expected results and verify
    # Baseline calculations
    base_fee = SIMULATION_BASE_FEE_PERCENT / 100  # 0.1% -> 0.001
    expected_baseline_revenue = 1000 * base_fee  # 1000 * 0.001 = 1.0
    assert np.isclose(result['baseline_revenue'], expected_baseline_revenue)

    # Simulated calculations
    new_fee = (SIMULATION_BASE_FEE_PERCENT + proposed_change) / 100 # 0.12% -> 0.0012
    percent_change_in_fee = proposed_change / SIMULATION_BASE_FEE_PERCENT # 0.02 / 0.1 = 0.2 (20%)
    percent_change_in_volume = -SIMULATION_ELASTICITY_CONSTANT * percent_change_in_fee # -0.5 * 0.2 = -0.1 (-10%)
    simulated_volume = 1000 * (1 + percent_change_in_volume) # 1000 * 0.9 = 900
    expected_simulated_revenue = simulated_volume * new_fee # 900 * 0.0012 = 1.08

    assert np.isclose(result['simulated_revenue'], expected_simulated_revenue)
    assert np.isclose(result['delta'], expected_simulated_revenue - expected_baseline_revenue)
    assert "Positive Impact" in result['recommendation']