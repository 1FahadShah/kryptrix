# tests/test_analytics.py

import pandas as pd
import numpy as np
import sys
import os

# Add project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.analytics import calculate_technical_indicators, detect_arbitrage, detect_anomalies
from config import SOURCES # Import sources for arbitrage test

def test_calculate_technical_indicators_happy_path():
    """
    Tests that the indicator calculation function works with valid data.
    """
    # 1. Arrange: Create a sample DataFrame with enough data
    data = {
        'timestamp': pd.to_datetime(pd.date_range(end=pd.Timestamp.now(), periods=40, freq='h')),
        'close': np.linspace(100, 150, 40),
        'volume_24h': np.random.uniform(1e6, 5e6, 40)
    }
    sample_df = pd.DataFrame(data)

    # 2. Act: Call the function we are testing
    result_df = calculate_technical_indicators(sample_df.copy())
    result = result_df.iloc[-1].to_dict() # Get the latest indicators

    # 3. Assert: Check if the main indicators are present
    assert isinstance(result, dict)
    assert 'SMA_10' in result
    assert 'SMA_30' in result
    assert 'EMA_14' in result
    assert 'RSI_14' in result
    assert 'VWAP_24h' in result
    assert 'Realized_Vol_30D' in result

    # Check a specific value for SMA10
    expected_sma10 = sample_df['close'].tail(10).mean()
    assert np.isclose(result['SMA_10'], expected_sma10)

def test_calculate_technical_indicators_not_enough_data():
    """
    Tests that the function returns an empty DataFrame if there isn't enough data.
    """
    data = {'close': [100, 101, 102, 103, 104]}
    sample_df = pd.DataFrame(data)
    result = calculate_technical_indicators(sample_df)
    assert result.empty

def test_detect_arbitrage_opportunity():
    """
    Tests that a clear arbitrage opportunity is correctly identified.
    """
    data = {
        'timestamp': pd.to_datetime(['2025-01-01 12:00', '2025-01-01 12:01']),
        'source': ['Binance', 'UniswapV3'],
        'price_usd': [100.0, 105.0] # A 5% difference
    }
    sample_df = pd.DataFrame(data)
    opportunities = detect_arbitrage(sample_df)

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity['source_a'] == 'Buy at Binance'
    assert opportunity['source_b'] == 'Sell at UniswapV3'
    assert np.isclose(opportunity['percent_diff'], 5.0)

def test_detect_anomalies_volume_spike():
    """
    Tests that a volume spike anomaly is detected.
    """
    # Arrange: 30 days of normal volume, with one huge spike at the end
    normal_volume = np.full(30, 100)
    spiked_volume = np.append(normal_volume, 1000) # 10x the average
    prices = np.linspace(100, 101, 31)
    timestamps = pd.to_datetime(pd.date_range(end=pd.Timestamp.now(), periods=31, freq='h'))
    df = pd.DataFrame({'timestamp': timestamps, 'close': prices, 'volume_24h': spiked_volume})

    # Act
    anomalies = detect_anomalies(df)

    # Assert
    assert len(anomalies) == 1
    assert anomalies[0]['anomaly_type'] == "Volume Spike"
    assert "exceeds threshold" in anomalies[0]['description']

def test_detect_anomalies_price_jump():
    """
    Tests that a price jump anomaly is detected.
    """
    # Arrange: A series of prices with a sudden >5% jump at the end
    prices = [100] * 30
    prices.append(106) # A 6% jump
    timestamps = pd.to_datetime(pd.date_range(end=pd.Timestamp.now(), periods=31, freq='h'))
    df = pd.DataFrame({'timestamp': timestamps, 'close': prices, 'volume_24h': [100]*31})

    # Act
    anomalies = detect_anomalies(df)

    # Assert
    assert len(anomalies) == 1
    assert anomalies[0]['anomaly_type'] == "Price Jump"
    assert "Price changed by 6.00%" in anomalies[0]['description']

def test_detect_anomalies_no_anomaly():
    """
    Tests that no anomaly is detected with stable data.
    """
    # Arrange: Stable price and volume data
    prices = np.linspace(100, 101, 30)
    volumes = np.full(30, 100)
    timestamps = pd.to_datetime(pd.date_range(end=pd.Timestamp.now(), periods=30, freq='h'))
    df = pd.DataFrame({'timestamp': timestamps, 'close': prices, 'volume_24h': volumes})

    # Act
    anomalies = detect_anomalies(df)

    # Assert
    assert len(anomalies) == 0