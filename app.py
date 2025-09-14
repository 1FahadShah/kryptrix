# app.py
import streamlit as st
from dashboard import layout, kpi_view, trading_view, feature_view, stakeholder_view

# --- Page Configuration ---
st.set_page_config(
    page_title="Kryptrix Analytics",
    page_icon="📈",
    layout="wide"
)

def main():
    """Main function to run the Streamlit app."""

    # --- Sidebar Navigation ---
    st.sidebar.title("Kryptrix Navigation")
    page = layout.setup_sidebar()

    # --- Page Routing ---
    if page == "KPI Dashboard":
        st.title("📈 KPI Dashboard")
        kpi_view.render_kpi_view() # We will uncomment this later
        # st.write("KPI View will be built here.")

    elif page == "Trading Analytics":
        st.title("💹 Trading Analytics")
        trading_view.render_trading_view() # We will uncomment this later
        #st.write("Trading Analytics View will be built here.")

    elif page == "Feature Simulator":
        st.title("🔬 Feature Simulator")
        feature_view.render_feature_view() # We will uncomment this later
        #st.write("Feature Simulator View will be built here.")

    elif page == "Stakeholder Reports":
        st.title("📄 Stakeholder Reports")
        stakeholder_view.render_stakeholder_view() # We will uncomment this later
        #st.write("Stakeholder Reports View will be built here.")

if __name__ == "__main__":
    main()