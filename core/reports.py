# core/reports.py

import sqlite3
import pandas as pd
from fpdf import FPDF
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import sys
import os

# Add project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import DB_PATH

# --- Configuration ---
CHART_DPI = 300
REPORT_DIR = "reports" # We will save reports in a dedicated folder

# --- Database Helpers ---
def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_token_id(conn, symbol):
    """Fetches the ID for a given token symbol."""
    result = conn.execute("SELECT id FROM tokens WHERE symbol = ?", (symbol,)).fetchone()
    if result:
        return result['id']
    raise ValueError(f"Token ID for {symbol} not found.")

# --- Charting Function ---
def create_price_chart(df: pd.DataFrame, token_symbol: str, output_path: str):
    """Creates and saves a simple price chart for the last 24 hours."""
    if df.empty:
        return

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df['timestamp'], df['price_usd'], color='blue', linewidth=2)

    ax.set_title(f'{token_symbol}/USD Price Trend (Last 24h)', fontsize=14)
    ax.set_ylabel('Price (USD)')
    ax.grid(True, linestyle='--', alpha=0.6)

    # Formatting the x-axis to show dates nicely
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    fig.autofmt_xdate()

    plt.tight_layout()
    plt.savefig(output_path, dpi=CHART_DPI)
    plt.close()

# --- PDF Generation Class ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Kryptrix Analytics Report', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(2)

    def chapter_body(self, data, is_table=False):
        self.set_font('Arial', '', 10)
        if is_table:
            # Simple table rendering
            col_width = self.w / (len(data[0]) + 0.5)
            self.set_font('Arial', 'B', 9)
            for header in data[0]:
                self.cell(col_width, 10, header, border=1)
            self.ln()
            self.set_font('Arial', '', 9)
            for row in data[1:]:
                for item in row:
                    self.cell(col_width, 10, str(item), border=1)
                self.ln()
        else:
            self.multi_cell(0, 5, data)
        self.ln()

# --- Main Report Generator ---
def generate_summary_report(token_symbol: str) -> str:
    """
    Generates a full PDF summary report for a given token.

    Returns:
        The file path of the generated PDF.
    """
    print(f"--- Generating report for {token_symbol} ---")
    conn = get_db_connection()
    token_id = get_token_id(conn, token_symbol)

    # 1. Fetch data
    df_prices = pd.read_sql_query("SELECT timestamp, price_usd FROM prices WHERE token_id = ? AND source = 'Binance' ORDER BY timestamp DESC LIMIT 100", conn, params=(token_id,))
    df_anomalies = pd.read_sql_query("SELECT timestamp, anomaly_type, description FROM anomalies WHERE token_id = ? ORDER BY timestamp DESC LIMIT 5", conn, params=(token_id,))
    df_arbitrage = pd.read_sql_query("SELECT source_a, source_b, percent_diff FROM arbitrage WHERE token_id = ? ORDER BY percent_diff DESC LIMIT 5", conn, params=(token_id,))
    kpi_data = conn.execute("SELECT price_usd, volume_24h FROM prices WHERE token_id = ? ORDER BY timestamp DESC LIMIT 1", (token_id,)).fetchone()

    # 2. Create chart
    chart_path = os.path.join(REPORT_DIR, f"{token_symbol}_price_chart.png")
    os.makedirs(REPORT_DIR, exist_ok=True)
    create_price_chart(df_prices, token_symbol, chart_path)

    # 3. Assemble PDF
    pdf = PDFReport()
    pdf.add_page()

    # Title
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f'Summary for {token_symbol} - {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1, 'C')
    pdf.ln(10)

    # KPIs
    pdf.chapter_title('Key Performance Indicators (KPIs)')
    if kpi_data:
        pdf.chapter_body(f"  - Latest Price: ${kpi_data['price_usd']:,.2f}\n  - 24h Volume: ${kpi_data['volume_24h']:,.2f}")
    else:
        pdf.chapter_body("  - No KPI data available.")

    # Chart
    if os.path.exists(chart_path):
        pdf.image(chart_path, x=None, y=None, w=pdf.w - 20)
        pdf.ln(5)

    # Anomalies Table
    pdf.chapter_title('Recent Anomalies')
    if not df_anomalies.empty:
        anomaly_table_data = [['Timestamp', 'Type', 'Description']]
        for index, row in df_anomalies.iterrows():
            anomaly_table_data.append([row['timestamp'][:16], row['anomaly_type'], row['description'][:50] + '...'])
        pdf.chapter_body(anomaly_table_data, is_table=True)
    else:
        pdf.chapter_body("  - No recent anomalies detected.")

    # Arbitrage Table
    pdf.chapter_title('Top Arbitrage Opportunities')
    if not df_arbitrage.empty:
        arbitrage_table_data = [['Buy Source', 'Sell Source', 'Profit %']]
        for index, row in df_arbitrage.iterrows():
            arbitrage_table_data.append([row['source_a'], row['source_b'], f"{row['percent_diff']:.3f}%"])
        pdf.chapter_body(arbitrage_table_data, is_table=True)
    else:
        pdf.chapter_body("  - No active arbitrage opportunities found.")

    # 4. Save PDF
    report_path = os.path.join(REPORT_DIR, f"{token_symbol}_Report_{datetime.now().strftime('%Y%m%d')}.pdf")
    pdf.output(report_path)
    print(f"--- Report successfully saved to: {report_path} ---")

    # Clean up temporary chart file
    os.remove(chart_path)
    conn.close()
    return report_path


if __name__ == '__main__':
    # Example of how to run the report generator directly for testing
    if len(sys.argv) > 1:
        token_to_report = sys.argv[1].upper()
    else:
        token_to_report = 'BTC' # Default to BTC if no argument is given

    generate_summary_report(token_to_report)