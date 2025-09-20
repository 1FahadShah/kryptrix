#!/bin/bash

# Step 1: Initialize the database structure
echo "🚀 Initializing database..."
python database/database_setup.py

# Step 2: Seed the database with initial historical data
echo "🌱 Seeding initial data..."
python scripts/seed_db.py

# Step 3: Start the background data pipeline
echo "📡 Starting data pipeline in the background..."
python main.py &

# Step 4: Start the Streamlit app in the foreground
echo "📊 Starting Streamlit dashboard..."
streamlit run app.py --server.port 7860