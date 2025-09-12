# core/data_fetcher.py
import asyncio
import httpx
import sqlite3
from sqlite3 import Error
from datetime import datetime, timezone
import json
from typing import Dict, List, Optional
import sys
import os

# Add project root to the Python path to allow importing from config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import configurations from the central config file
from config import (
    DB_PATH,
    TOKENS,
    MAX_RETRIES,
    RETRY_DELAY,
    MAX_CONCURRENT_REQUESTS,
    BINANCE_API_URL,
    COINGECKO_API_URL,
    UNISWAP_V3_SUBGRAPH_URL,
)

# ---------------- Database Helpers ----------------
def create_connection(db_path=DB_PATH) -> Optional[sqlite3.Connection]:
    # This function is now slightly redundant with database_setup.py,
    # but it's fine to keep it here for this module's self-sufficiency.
    # In a larger app, you might create a shared db connection manager.
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except Error as e:
        print(f"[DB ERROR] {e}")
        return None

def insert_price(conn: sqlite3.Connection, token_id: int, source: str, price_usd: float, volume_24h: float, raw_data: dict):
    # Added 'source' to the prices table to track where the data came from
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO prices (token_id, source, price_usd, volume_24h, raw_data) VALUES (?, ?, ?, ?, ?)",
            (token_id, source, price_usd, volume_24h, json.dumps(raw_data))
        )
        conn.commit()
    except Error as e:
        print(f"[DB INSERT ERROR] {e}")

# The rest of the database helpers (log_api_health, get_token_id) remain the same...

def log_api_health(conn: sqlite3.Connection, source: str, status: str, response_time_ms: float = None,
                   error_message: str = None, raw_data: dict = None):
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO api_health (source, status, response_time_ms, error_message, raw_data) VALUES (?, ?, ?, ?, ?)",
            (source, status, response_time_ms, error_message, json.dumps(raw_data) if raw_data else None)
        )
        conn.commit()
    except Error as e:
        print(f"[DB API HEALTH ERROR] {e}")

def get_token_id(conn: sqlite3.Connection, symbol: str) -> int:
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tokens WHERE symbol = ?", (symbol,))
        result = cursor.fetchone()
        if result:
            return result[0]
        raise ValueError(f"Token {symbol} not found in DB. Did you run scripts/seed_db.py?")
    except Error as e:
        print(f"[DB GET TOKEN ERROR] {e}")
        raise


# ---------------- Fetch Helpers ----------------
async def fetch_with_retry(client: httpx.AsyncClient, url: str, source_name: str, method="GET", payload=None):
    for attempt in range(1, MAX_RETRIES + 1):
        start_time = datetime.now(timezone.utc)
        try:
            if method.upper() == "POST":
                resp = await client.post(url, json=payload, timeout=10.0)
            else:
                resp = await client.get(url, timeout=10.0)

            resp.raise_for_status()
            elapsed_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return resp.json(), elapsed_ms
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP Error: {e.response.status_code} for URL: {e.request.url}"
            print(f"[{source_name} ATTEMPT {attempt}/{MAX_RETRIES}] {error_message}")
            if attempt == MAX_RETRIES:
                return {"error": error_message, "raw_response": e.response.text}, (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        except Exception as e:
            error_message = str(e)
            print(f"[{source_name} ATTEMPT {attempt}/{MAX_RETRIES}] General Error: {error_message}")
            if attempt == MAX_RETRIES:
                 return {"error": error_message}, (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        await asyncio.sleep(RETRY_DELAY)


# ---------------- Exchange Fetchers ----------------
async def fetch_binance(client: httpx.AsyncClient, token: Dict, conn: sqlite3.Connection, semaphore: asyncio.Semaphore):
    async with semaphore:
        url = f"{BINANCE_API_URL}/ticker/24hr?symbol={token['binance_id']}"
        data, elapsed_ms = await fetch_with_retry(client, url, "Binance")
        try:
            token_id = get_token_id(conn, token["symbol"])
            if "error" not in data:
                insert_price(conn, token_id, "Binance", float(data["lastPrice"]), float(data["quoteVolume"]), data)
                log_api_health(conn, "Binance", "success", elapsed_ms, None, data)
            else:
                log_api_health(conn, "Binance", "error", elapsed_ms, data["error"], data.get("raw_response"))
        except Exception as e:
            log_api_health(conn, "Binance", "error", elapsed_ms, str(e))
        return data

async def fetch_coingecko(client: httpx.AsyncClient, token: Dict, conn: sqlite3.Connection, semaphore: asyncio.Semaphore):
    async with semaphore:
        url = f"{COINGECKO_API_URL}/simple/price?ids={token['coingecko_id']}&vs_currencies=usd&include_24hr_vol=true"
        data, elapsed_ms = await fetch_with_retry(client, url, "CoinGecko")
        try:
            token_id = get_token_id(conn, token["symbol"])
            if "error" not in data and token["coingecko_id"] in data:
                price_data = data[token["coingecko_id"]]
                insert_price(conn, token_id, "CoinGecko", price_data["usd"], price_data["usd_24h_vol"], data)
                log_api_health(conn, "CoinGecko", "success", elapsed_ms, None, data)
            else:
                error_msg = data.get("error", "Token data not found in response")
                log_api_health(conn, "CoinGecko", "error", elapsed_ms, error_msg, data.get("raw_response"))
        except Exception as e:
            log_api_health(conn, "CoinGecko", "error", elapsed_ms, str(e))
        return data

async def fetch_eth_usd(client: httpx.AsyncClient, semaphore: asyncio.Semaphore) -> float:
    async with semaphore:
        url = f"{BINANCE_API_URL}/ticker/price?symbol=ETHUSDT"
        data, _ = await fetch_with_retry(client, url, "Binance-ETH")
        if "price" in data:
            return float(data["price"])
        return 2000.0  # Fallback

async def fetch_uniswap_v3(client: httpx.AsyncClient, token: Dict, conn: sqlite3.Connection, eth_usd: float, semaphore: asyncio.Semaphore):
    async with semaphore:
        query = {
            "query": f"""
            {{
                pools(
                    first: 5,
                    orderBy: totalValueLockedUSD,
                    orderDirection: desc,
                    where: {{
                        or: [
                            {{ token0: "{token['uniswap_id'].lower()}" }},
                            {{ token1: "{token['uniswap_id'].lower()}" }}
                        ]
                    }}
                ) {{
                    token0 {{ symbol, derivedETH }}
                    token1 {{ symbol, derivedETH }}
                    volumeUSD
                    token0Price
                    token1Price
                }}
            }}
            """
        }

        data, elapsed_ms = await fetch_with_retry(client, UNISWAP_V3_SUBGRAPH_URL, "UniswapV3", method="POST", payload=query)

        try:
            token_id = get_token_id(conn, token["symbol"])
            if "error" not in data and data.get("data", {}).get("pools"):
                pools = data["data"]["pools"]
                if not pools:
                    # This handles cases where the API returns an empty pool list
                    raise ValueError(f"No pools found for {token['symbol']} in Uniswap response.")

                pool = pools[0]
                price_usd = 0.0

                if pool['token0']['symbol'].upper() in [token['symbol'], 'W'+token['symbol']]:
                    price_usd = float(pool['token0']['derivedETH']) * eth_usd
                elif pool['token1']['symbol'].upper() in [token['symbol'], 'W'+token['symbol']]:
                    price_usd = float(pool['token1']['derivedETH']) * eth_usd
                else:
                    raise ValueError("Could not determine price from pool.")

                volume_usd = float(pool["volumeUSD"])
                insert_price(conn, token_id, "UniswapV3", price_usd, volume_usd, data)
                log_api_health(conn, "UniswapV3", "success", elapsed_ms, None, data)
            else:
                error_msg = data.get("errors", [{}])[0].get("message", f"No pools found or data error for {token['symbol']}")
                log_api_health(conn, "UniswapV3", "error", elapsed_ms, error_msg, data)

        except Exception as e:
            log_api_health(conn, "UniswapV3", "error", elapsed_ms, str(e))
        return data

# ---------------- Runner ----------------
async def fetch_all_prices(tokens: List[Dict] = TOKENS):
    conn = create_connection()
    if not conn:
        print("Failed to connect to DB. Fetcher cannot run.")
        return

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    async with httpx.AsyncClient(follow_redirects=True) as client:
        eth_usd = await fetch_eth_usd(client, semaphore)

        tasks = []
        for token in tokens:
            if token.get("binance_id"):
                tasks.append(fetch_binance(client, token, conn, semaphore))
            if token.get("coingecko_id"):
                tasks.append(fetch_coingecko(client, token, conn, semaphore))
            if token.get("uniswap_id") and token['symbol'] != 'ETH':
                tasks.append(fetch_uniswap_v3(client, token, conn, eth_usd, semaphore))

        print(f"Starting to fetch data for {len(tasks)} tasks...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        print("All fetching tasks completed.")

    conn.close()
    return results

# ---------------- Main ----------------
if __name__ == "__main__":
    print("Running data fetcher as a standalone script...")
    # Add a column to prices table to track source
    # This is a one-time migration. A better approach is using a migration tool.
    try:
        conn = create_connection()
        conn.execute("ALTER TABLE prices ADD COLUMN source TEXT;")
        conn.commit()
        print("Added 'source' column to 'prices' table.")
        conn.close()
    except sqlite3.OperationalError:
        # Column likely already exists, which is fine.
        pass
    except Exception as e:
        print(f"Could not alter table: {e}")

    asyncio.run(fetch_all_prices())
    print("Data fetcher run complete.")