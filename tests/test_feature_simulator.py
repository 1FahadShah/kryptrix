# tests/test_feature_simulator.py

import pandas as pd
import numpy as np
import sys
import os

# Add project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.feature_simulator import simulate_fee_change_impact
from config import SIMULATION_BASE_FEE_PERCENT, SIMULATION_ELASTICITY_CONSTANT

def test_simulate_fee_change_impact_positive():
    """
    Tests the fee simulation with a proposed fee INCREASE.
    """
    # 1. Arrange: Create sample volume data and a proposed fee change
    sample_volume = pd.Series([1000] * 10)
    proposed_change = 0.02 # A 0.02% increase

    # 2. Act: Run the simulation
    result = simulate_fee_change_impact(sample_volume, proposed_change)

    # 3. Assert
    # Baseline calculations
    base_fee = SIMULATION_BASE_FEE_PERCENT / 100
    expected_baseline_revenue = 1000 * base_fee
    assert np.isclose(result['baseline_revenue'], expected_baseline_revenue)

    # Simulated calculations
    new_fee = (SIMULATION_BASE_FEE_PERCENT + proposed_change) / 100
    percent_change_in_fee = proposed_change / SIMULATION_BASE_FEE_PERCENT
    percent_change_in_volume = -SIMULATION_ELASTICITY_CONSTANT * percent_change_in_fee
    simulated_volume = 1000 * (1 + percent_change_in_volume)
    expected_simulated_revenue = simulated_volume * new_fee

    assert np.isclose(result['simulated_revenue'], expected_simulated_revenue)
    assert np.isclose(result['delta'], expected_simulated_revenue - expected_baseline_revenue)
    assert "Positive Impact" in result['recommendation']

def test_simulate_fee_change_impact_negative():
    """
    Tests the fee simulation with a proposed fee DECREASE.
    """
    # 1. Arrange
    sample_volume = pd.Series([1000] * 10)
    proposed_change = -0.02 # A 0.02% decrease

    # 2. Act
    result = simulate_fee_change_impact(sample_volume, proposed_change)

    # 3. Assert
    assert "Negative Impact" in result['recommendation']
    assert result['delta'] < 0