# tests/test_analytics.py

import pandas as pd
import numpy as np
import sys
import os

# Add project root to the Python path so we can import from 'core'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.analytics import calculate_technical_indicators, detect_arbitrage

def test_calculate_technical_indicators_happy_path():
    """
    Tests that the indicator calculation function works with valid data.
    """
    # 1. Arrange: Create a sample DataFrame with enough data
    data = {'close': np.linspace(100, 150, 40)} # 40 data points from 100 to 150
    sample_df = pd.DataFrame(data)

    # 2. Act: Call the function we are testing
    result = calculate_technical_indicators(sample_df)

    # 3. Assert: Check if the output is correct
    assert isinstance(result, dict)
    assert 'SMA_10' in result
    assert 'SMA_30' in result
    assert 'EMA_14' in result
    assert 'RSI_14' in result

    # Check a specific value: the SMA_10 of the last 10 points
    # Last 10 values are from 137.17 to 150. Their average should be ~143.59
    expected_sma10 = sample_df['close'].tail(10).mean()
    assert np.isclose(result['SMA_10'], expected_sma10)

def test_calculate_technical_indicators_not_enough_data():
    """
    Tests that the function returns an empty dict if there isn't enough data.
    """
    # 1. Arrange: Create a DataFrame with only 5 data points
    data = {'close': [100, 101, 102, 103, 104]}
    sample_df = pd.DataFrame(data)

    # 2. Act
    result = calculate_technical_indicators(sample_df)

    # 3. Assert
    assert result == {}

def test_detect_arbitrage_opportunity():
    """
    Tests that a clear arbitrage opportunity is correctly identified.
    """
    # 1. Arrange: Create data with a significant price difference
    data = {
        'timestamp': pd.to_datetime(['2025-01-01 12:00', '2025-01-01 12:01']),
        'source': ['Binance', 'UniswapV3'],
        'price_usd': [100.0, 105.0] # A 5% difference
    }
    sample_df = pd.DataFrame(data)

    # 2. Act
    opportunities = detect_arbitrage(sample_df)

    # 3. Assert
    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity['source_a'] == 'Buy at Binance'
    assert opportunity['source_b'] == 'Sell at UniswapV3'
    assert np.isclose(opportunity['percent_diff'], 5.0)