# tests/test_data_fetcher.py

import pytest
import asyncio
import httpx # <--- IMPORT HTTPROXY
import sys
import os

# Add project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.data_fetcher import fetch_binance

# Mark the test as an asyncio test
@pytest.mark.asyncio
async def test_fetch_binance_with_mocking(monkeypatch):
    """
    Tests the fetch_binance function by mocking the API call and DB write.
    `monkeypatch` is a pytest fixture for safely modifying code during tests.
    """
    # 1. Arrange: Define what our fake API call will return
    mock_api_response = {
        "symbol": "BTCUSDT",
        "lastPrice": "50000.00",
        "quoteVolume": "1000000.00"
    }

    # Create a mock async function to replace httpx.get
    class MockAsyncResponse:
        def json(self):
            return mock_api_response
        def raise_for_status(self):
            pass # Do nothing, assume success

    async def mock_get(*args, **kwargs):
        return MockAsyncResponse()

    # Use monkeypatch to replace the real httpx GET with our fake one
    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

    # Arrange: Keep track of what gets sent to the database
    db_call_args = {}
    def mock_insert_price(conn, token_id, source, price_usd, volume_24h, raw_data):
        db_call_args['token_id'] = token_id
        db_call_args['source'] = source
        db_call_args['price_usd'] = price_usd
        db_call_args['volume_24h'] = volume_24h

    # Replace the real database insert function with our tracker
    monkeypatch.setattr("core.data_fetcher.insert_price", mock_insert_price)
    monkeypatch.setattr("core.data_fetcher.log_api_health", lambda *args, **kwargs: None) # Ignore health logging
    monkeypatch.setattr("core.data_fetcher.get_token_id", lambda conn, symbol: 1) # Assume token_id is 1

    # 2. Act: Call the function we are testing
    # --- FIX IS HERE ---
    await fetch_binance(
        client=httpx.AsyncClient(), # Pass a REAL client instance
        token={"symbol": "BTC", "binance_id": "BTCUSDT"},
        conn=None,
        semaphore=asyncio.Semaphore(1)
    )
    # --- END OF FIX ---

    # 3. Assert: Check if the database function was called with the correct data
    assert db_call_args['token_id'] == 1
    assert db_call_args['source'] == "Binance"
    assert db_call_args['price_usd'] == 50000.00
    assert db_call_args['volume_24h'] == 1000000.00