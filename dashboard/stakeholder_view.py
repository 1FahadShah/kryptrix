# dashboard/stakeholder_view.py

import streamlit as st
import sqlite3
import sys
import os

# Add project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.reports import generate_summary_report
from config import DB_PATH, TOKENS

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)

def insert_stakeholder_request(request_text: str):
    """Saves a stakeholder's request to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO stakeholder_requests (request) VALUES (?)", (request_text,))
    conn.commit()
    conn.close()

def render_stakeholder_view():
    """Renders the Stakeholder Reports view."""

    st.subheader("Stakeholder Interaction Portal")

    # --- Section 1: Stakeholder Request Form ---
    st.markdown("#### Submit a Data Request")
    with st.form(key="request_form"):
        request_text = st.text_area(
            "Enter your question or data request here:",
            height=150,
            placeholder="e.g., 'Can we get a breakdown of arbitrage opportunities for ETH in the last 7 days?'"
        )
        submit_button = st.form_submit_button(label="Submit Request")

        if submit_button:
            if request_text:
                insert_stakeholder_request(request_text)
                st.success("Your request has been successfully submitted and logged!")
            else:
                st.warning("Please enter a request before submitting.")

    st.markdown("---")

    # --- Section 2: On-Demand Report Generation ---
    st.markdown("#### Generate PDF Report")
    token_symbols = [token['symbol'] for token in TOKENS]
    selected_token = st.selectbox("Select a token for the report:", token_symbols)

    if st.button("Generate Report"):
        with st.spinner(f"Generating PDF report for {selected_token}..."):
            try:
                report_path = generate_summary_report(selected_token)

                with open(report_path, "rb") as pdf_file:
                    pdf_bytes = pdf_file.read()

                st.download_button(
                    label="Download Report",
                    data=pdf_bytes,
                    file_name=os.path.basename(report_path),
                    mime="application/pdf"
                )
                st.success(f"Report for {selected_token} is ready for download.")

            except Exception as e:
                st.error(f"Failed to generate report: {e}")