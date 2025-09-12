# config.py
import os

# ------------------ Database Config ------------------
DB_DIR = "database"
DB_PATH = os.path.join(DB_DIR, "kryptrix.db")


# ------------------ Token Config ------------------
# Central repository for all tokens the system will track.
# Adding a new token here is all that's needed for the fetcher to pick it up.
TOKENS = [
    {
        "symbol": "BTC",
        "name": "Bitcoin",
        "binance_id": "BTCUSDT",
        "coingecko_id": "bitcoin",
        "uniswap_id": "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599" # This is WBTC for Uniswap
    },
    {
        "symbol": "ETH",
        "name": "Ethereum",
        "binance_id": "ETHUSDT",
        "coingecko_id": "ethereum",
        "uniswap_id": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2" # This is WETH for Uniswap
    },
    # Add more tokens here in the future
]


# ------------------ API & Fetcher Config ------------------
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
MAX_CONCURRENT_REQUESTS = 10  # Throttling semaphore limit

# API Endpoints
BINANCE_API_URL = "https://api.binance.com/api/v3"
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
UNISWAP_V3_SUBGRAPH_URL = "https://api.thegraph.com/subgraphs/id/0xed93b2ea13291fb4689232322a46c1e5b228b348"