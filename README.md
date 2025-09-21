---
title: Kryptrix
emoji: 💹
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: "1.49.1"
app_file: app.py
pinned: false
---

# Kryptrix 💹

[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.49.1-orange)](https://streamlit.io/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Overview

**Kryptrix** is a **real-time cryptocurrency analytics and simulation platform**, designed for both **Centralized (CEX) and Decentralized (DEX) exchanges**. It provides:

- ✅ **Real-time Trading Analytics**:
  Fetches live prices from Binance, CoinGecko, and optionally Uniswap.
  Computes indicators: SMA10/30, EMA, RSI14, VWAP24h, realized volatility.
  Detects arbitrage opportunities between CEX and DEX.
  Detects anomalies: volume spikes, price jumps, z-score deviations.

- ✅ **Feature Simulation (A/B Testing)**:
  Models the impact of changing fees, latency, or UI conversion.
  Shows baseline vs simulated revenue, delta, and actionable recommendations.

- ✅ **KPI Dashboard**:
  Visualizes Last Price, 24h Volume, VWAP, Active Arbitrage, API Health, Anomalies.
  Interactive charts and tables powered by **Plotly**.

- ✅ **Stakeholder Requests & Reporting**:
  Input portal for stakeholder questions.
  Generates **PDF reports** with KPIs, top arbitrage opportunities, anomalies, and charts.

---

## Getting Started

### Run Locally

```bash
git clone https://github.com/1FahadShah/kryptrix.git
cd kryptrix
python -m venv venv
source venv/bin/activate  # Mac/Linux
# .\venv\Scripts\activate  # Windows
pip install -r requirements.txt
streamlit run app.py
```

## Hugging Face Space

Visit the live demo: kryptrix.1fahadshah.com

## Project Structure

```
kryptrix/
├── core/ # Backend logic and analytics
├── dashboard/ # Streamlit UI pages
├── database/ # SQLite setup and migrations
├── scripts/ # Helper scripts like seed_db.py
├── tests/ # Unit tests
├── app.py # Streamlit entrypoint
├── config.py # API endpoints and thresholds
├── requirements.txt
├── Dockerfile
└── README.md
```

## Deployment

- Hugging Face Space: Auto-deploy via GitHub Actions.
- Local Development: Use streamlit run app.py.
- Docker: docker build -t kryptrix . && docker run -p 8501:8501 kryptrix

## License

This project is licensed under the MIT License
