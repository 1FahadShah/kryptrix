# tests/test_data_fetcher.py

import pytest
import asyncio
import httpx
import sys
import os

# Add project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.data_fetcher import fetch_binance, fetch_coingecko, fetch_uniswap_v3

# --- Mock Response Class ---
class MockAsyncResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code
        self.request = httpx.Request("GET", "https://test.com")

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code != 200:
            raise httpx.HTTPStatusError(
                message=f"Error: {self.status_code}",
                request=self.request,
                response=httpx.Response(self.status_code, json=self._json_data)
            )

# --- Binance Tests ---
@pytest.mark.asyncio
async def test_fetch_binance_success(monkeypatch):
    """ Tests the fetch_binance function for a successful API call. """
    mock_api_response = {"lastPrice": "50000.00", "quoteVolume": "1000000.00"}

    async def mock_get(*args, **kwargs):
        return MockAsyncResponse(mock_api_response)

    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

    db_call_args = {}
    def mock_insert_price(conn, token_id, source, price_usd, volume_24h, raw_data):
        db_call_args.update(locals())

    monkeypatch.setattr("core.data_fetcher.insert_price", mock_insert_price)
    monkeypatch.setattr("core.data_fetcher.log_api_health", lambda *args, **kwargs: None)
    monkeypatch.setattr("core.data_fetcher.get_token_id", lambda conn, symbol: 1)

    await fetch_binance(httpx.AsyncClient(), {"symbol": "BTC", "binance_id": "BTCUSDT"}, None, asyncio.Semaphore(1))

    assert db_call_args['source'] == "Binance"
    assert db_call_args['price_usd'] == 50000.00

@pytest.mark.asyncio
async def test_fetch_binance_api_error(monkeypatch):
    """ Tests the fetch_binance function when the API returns an error. """
    async def mock_get(*args, **kwargs):
        # Simulate a failed API call after retries
        return {"error": "HTTP Error: 500 for URL: https://test.com", "raw_response": "{}"}, 50.0

    # FIX: We now mock fetch_with_retry directly as it's the source of the error tuple
    monkeypatch.setattr("core.data_fetcher.fetch_with_retry", mock_get)

    health_log_args = {}
    # FIX: The mock signature now accepts all possible arguments
    def mock_log_health(conn, source, status, response_time_ms=None, error_message=None, raw_data=None):
        health_log_args.update(locals())

    monkeypatch.setattr("core.data_fetcher.log_api_health", mock_log_health)
    monkeypatch.setattr("core.data_fetcher.get_token_id", lambda conn, symbol: 1)

    await fetch_binance(httpx.AsyncClient(), {"symbol": "BTC", "binance_id": "BTCUSDT"}, None, asyncio.Semaphore(1))

    assert health_log_args['source'] == "Binance"
    assert health_log_args['status'] == "error"
    assert "HTTP Error: 500" in health_log_args['error_message']

# --- CoinGecko Tests ---
@pytest.mark.asyncio
async def test_fetch_coingecko_success(monkeypatch):
    """ Tests the fetch_coingecko function for a successful API call. """
    mock_api_response = {"bitcoin": {"usd": 51000.00, "usd_24h_vol": 1200000.00}}

    async def mock_get(*args, **kwargs):
        return MockAsyncResponse(mock_api_response)

    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

    db_call_args = {}
    def mock_insert_price(conn, token_id, source, price_usd, volume_24h, raw_data):
        db_call_args.update(locals())

    monkeypatch.setattr("core.data_fetcher.insert_price", mock_insert_price)
    monkeypatch.setattr("core.data_fetcher.log_api_health", lambda *args, **kwargs: None)
    monkeypatch.setattr("core.data_fetcher.get_token_id", lambda conn, symbol: 1)

    await fetch_coingecko(httpx.AsyncClient(), {"symbol": "BTC", "coingecko_id": "bitcoin"}, None, asyncio.Semaphore(1))

    assert db_call_args['source'] == "CoinGecko"
    assert db_call_args['price_usd'] == 51000.00

# --- Uniswap Tests ---
@pytest.mark.asyncio
async def test_fetch_uniswap_v3_success(monkeypatch):
    """ Tests the fetch_uniswap_v3 function for a successful GraphQL call. """
    mock_api_response = {
        "data": {"pools": [{"token0": {"symbol": "WBTC", "derivedETH": "25.0"}, "token1": {"symbol": "WETH"}, "volumeUSD": "3000000.00"}]}
    }

    async def mock_post(*args, **kwargs):
        return MockAsyncResponse(mock_api_response)

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    db_call_args = {}
    def mock_insert_price(conn, token_id, source, price_usd, volume_24h, raw_data):
        db_call_args.update(locals())

    monkeypatch.setattr("core.data_fetcher.insert_price", mock_insert_price)
    monkeypatch.setattr("core.data_fetcher.log_api_health", lambda *args, **kwargs: None)
    monkeypatch.setattr("core.data_fetcher.get_token_id", lambda conn, symbol: 1)

    await fetch_uniswap_v3(httpx.AsyncClient(), {"symbol": "BTC", "uniswap_id": "0x..."}, None, eth_usd=2000.0, semaphore=asyncio.Semaphore(1))

    assert db_call_args['source'] == "UniswapV3"
    assert db_call_args['price_usd'] == 50000.00 # 25.0 * 2000.0