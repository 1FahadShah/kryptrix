# core/data_fetcher.py
import asyncio
import httpx
import sqlite3
from sqlite3 import Error
from datetime import datetime
import json
import os
from typing import Dict, List, Optional

# ---------------- Database Config ----------------
DB_DIR = "database"
DB_PATH = os.path.join(DB_DIR, "kryptrix.db")

# ---------------- Token Config ----------------
TOKENS = [
    {
        "symbol": "BTC",
        "name": "Bitcoin",
        "binance_id": "BTCUSDT",
        "coingecko_id": "bitcoin",
        "uniswap_id": "0x123..."
    },
    {
        "symbol": "ETH",
        "name": "Ethereum",
        "binance_id": "ETHUSDT",
        "coingecko_id": "ethereum",
        "uniswap_id": "0x456..."
    },
]

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
MAX_CONCURRENT_REQUESTS = 10  # throttling semaphore

# ---------------- Database Helpers ----------------
def create_connection(db_path=DB_PATH) -> Optional[sqlite3.Connection]:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except Error as e:
        print(f"[DB ERROR] {e}")
        return None

def insert_price(conn: sqlite3.Connection, token_id: int, price_usd: float, volume_24h: float, raw_data: dict):
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO prices (token_id, price_usd, volume_24h, raw_data) VALUES (?, ?, ?, ?)",
            (token_id, price_usd, volume_24h, json.dumps(raw_data))
        )
        conn.commit()
    except Error as e:
        print(f"[DB INSERT ERROR] {e}")

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
        raise ValueError(f"Token {symbol} not found in DB.")
    except Error as e:
        print(f"[DB GET TOKEN ERROR] {e}")
        raise

# ---------------- Fetch Helpers ----------------
async def fetch_with_retry(client: httpx.AsyncClient, url: str, source_name: str, method="GET", payload=None):
    for attempt in range(1, MAX_RETRIES + 1):
        start_time = datetime.utcnow()
        try:
            if method.upper() == "POST":
                resp = await client.post(url, json=payload, timeout=10.0)
            else:
                resp = await client.get(url, timeout=10.0)
            resp.raise_for_status()
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            return resp.json(), elapsed_ms
        except Exception as e:
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)
            else:
                return {"error": str(e)}, elapsed_ms

# ---------------- Exchange Fetchers ----------------
async def fetch_binance(client: httpx.AsyncClient, token: Dict, conn: sqlite3.Connection, semaphore: asyncio.Semaphore):
    async with semaphore:
        data, elapsed_ms = await fetch_with_retry(client, f"https://api.binance.com/api/v3/ticker/24hr?symbol={token['binance_id']}", "Binance")
        try:
            token_id = get_token_id(conn, token["symbol"])
            if "error" not in data:
                insert_price(conn, token_id, float(data["lastPrice"]), float(data["volume"]), data)
                log_api_health(conn, "Binance", "success", elapsed_ms, None, data)
            else:
                log_api_health(conn, "Binance", "error", elapsed_ms, data["error"])
        except Exception as e:
            log_api_health(conn, "Binance", "error", elapsed_ms, str(e))
        return data

async def fetch_coingecko(client: httpx.AsyncClient, token: Dict, conn: sqlite3.Connection, semaphore: asyncio.Semaphore):
    async with semaphore:
        data, elapsed_ms = await fetch_with_retry(
            client,
            f"https://api.coingecko.com/api/v3/simple/price?ids={token['coingecko_id']}&vs_currencies=usd&include_24hr_vol=true",
            "CoinGecko"
        )
        try:
            token_id = get_token_id(conn, token["symbol"])
            if "error" not in data and token["coingecko_id"] in data:
                price = data[token["coingecko_id"]]["usd"]
                volume = data[token["coingecko_id"]]["usd_24h_vol"]
                insert_price(conn, token_id, price, volume, data)
                log_api_health(conn, "CoinGecko", "success", elapsed_ms, None, data)
            else:
                log_api_health(conn, "CoinGecko", "error", elapsed_ms, data.get("error", "Missing token data"))
        except Exception as e:
            log_api_health(conn, "CoinGecko", "error", elapsed_ms, str(e))
        return data

async def fetch_eth_usd(client: httpx.AsyncClient, semaphore: asyncio.Semaphore) -> float:
    async with semaphore:
        data, _ = await fetch_with_retry(client, "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT", "Binance-ETH")
        if "price" in data:
            return float(data["price"])
        return 2000.0  # fallback

async def fetch_uniswap_v3(client: httpx.AsyncClient, token: Dict, conn: sqlite3.Connection, eth_usd: float, semaphore: asyncio.Semaphore):
    async with semaphore:
        query = {
            "query": f"""
            {{
              pools(first: 1, orderBy: totalValueLockedUSD, orderDirection: desc,
                    where: {{ token0: "{token['uniswap_id'].lower()}" }}) {{
                token0Price
                token1Price
                volumeUSD
              }}
            }}
            """
        }
        start_time = datetime.utcnow()
        try:
            resp = await client.post(
                "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3",
                json=query,
                timeout=10.0
            )
            resp.raise_for_status()
            data = resp.json()
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            token_id = get_token_id(conn, token["symbol"])
            pools = data.get("data", {}).get("pools", [])
            if not pools:
                log_api_health(conn, "UniswapV3", "error", elapsed_ms, "No pools found")
                return {"error": "No pools found"}

            pool = pools[0]
            derived_eth = float(pool.get("token1Price", 0))
            volume_usd = float(pool.get("volumeUSD", 0))
            price_usd = derived_eth * eth_usd

            insert_price(conn, token_id, price_usd, volume_usd, data)
            log_api_health(conn, "UniswapV3", "success", elapsed_ms, None, data)
            return data
        except Exception as e:
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            log_api_health(conn, "UniswapV3", "error", elapsed_ms, str(e))
            return {"error": str(e)}

# ---------------- Runner ----------------
async def fetch_all_prices(tokens: List[Dict] = TOKENS):
    conn = create_connection()
    if not conn:
        print("Failed to connect to DB")
        return

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    async with httpx.AsyncClient() as client:
        eth_usd = await fetch_eth_usd(client, semaphore)
        tasks = []
        for token in tokens:
            tasks.append(fetch_binance(client, token, conn, semaphore))
            tasks.append(fetch_coingecko(client, token, conn, semaphore))
            tasks.append(fetch_uniswap_v3(client, token, conn, eth_usd, semaphore))
        results = await asyncio.gather(*tasks)

    conn.close()
    return results

# ---------------- Main ----------------
if __name__ == "__main__":
    asyncio.run(fetch_all_prices())
