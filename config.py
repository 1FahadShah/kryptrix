# config.py
import os
from dotenv import load_dotenv

# Load variables from .env file into the environment
load_dotenv()

# --- Read the API Key from the environment ---
THE_GRAPH_API_KEY = os.getenv("THE_GRAPH_API_KEY")
if not THE_GRAPH_API_KEY:
    # This provides a helpful error if the .env file is missing or the key isn't set
    raise ValueError("THE_GRAPH_API_KEY not found in .env file. Please create it.")

# ------------------ Database Config ------------------
DB_DIR = "database"
DB_PATH = os.path.join(DB_DIR, "kryptrix.db")


# ------------------ Token Config ------------------
TOKENS = [
    {
        "symbol": "BTC",
        "name": "Bitcoin",
        "binance_id": "BTCUSDT",
        "coingecko_id": "bitcoin",
        "uniswap_id": "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599" # WBTC
    },
    {
        "symbol": "ETH",
        "name": "Ethereum",
        "binance_id": "ETHUSDT",
        "coingecko_id": "ethereum",
        "uniswap_id": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2" # WETH
    },
]


# ------------------ API & Fetcher Config ------------------
MAX_RETRIES = 3
RETRY_DELAY = 2
MAX_CONCURRENT_REQUESTS = 10

# API Endpoints
BINANCE_API_URL = "https://api.binance.com/api/v3"
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"

# --- Use the API Key to build the official, reliable Uniswap URL ---
UNISWAP_SUBGRAPH_ID = "5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV" # The ID you found
UNISWAP_V3_SUBGRAPH_URL = f"https://gateway.thegraph.com/api/{THE_GRAPH_API_KEY}/subgraphs/id/{UNISWAP_SUBGRAPH_ID}"


# ------------------ Feature Simulation Config ------------------
# A simple constant representing how sensitive trade volume is to fee changes.
# 0.5 means a 10% fee increase might lead to a 5% volume decrease.
SIMULATION_ELASTICITY_CONSTANT = 0.5
# The baseline fee our exchange charges, for revenue calculations (e.g., 0.1%)
SIMULATION_BASE_FEE_PERCENT = 0.1