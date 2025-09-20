# run.py
import subprocess
import sys
import os
import signal
import atexit

bg_process = None

def cleanup():
    """Ensure background process is terminated on script exit."""
    global bg_process
    if bg_process and bg_process.poll() is None:
        print("\n🛑 Terminating background data pipeline...")
        try:
            os.kill(bg_process.pid, signal.SIGTERM)
            bg_process.wait(timeout=5)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            print("⚠️ Force killing background process...")
            bg_process.kill()
        print("✅ Pipeline terminated.")

def run_command(command_args, description):
    """Runs a setup command using its file path and exits if it fails."""
    print(f"🚀 {description}...")
    try:
        # --- FIX IS HERE: We now run the script by its file path directly ---
        result = subprocess.run(
            [sys.executable] + command_args, check=True, capture_output=True, text=True
        )
        print(f"✅ {description} complete.")
    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR: {description} failed.")
        print(e.stderr) # Print the actual error from the script
        sys.exit(1)

def main():
    atexit.register(cleanup)

    # --- FIX IS HERE: We pass the file paths as a list ---
    run_command(["database/database_setup.py"], "Initializing database")
    run_command(["scripts/seed_db.py"], "Seeding initial data")

    # Start the background data pipeline
    print("📡 Starting background data pipeline...")
    global bg_process
    bg_process = subprocess.Popen([sys.executable, "main.py"])
    print(f"✅ Data pipeline started with PID: {bg_process.pid}")

    # Start the Streamlit app
    print("📊 Starting Streamlit dashboard...")
    try:
        subprocess.run(
            ["streamlit", "run", "app.py", "--server.port", "8501", "--server.headless", "true"],
            check=True
        )
    finally:
        cleanup()

if __name__ == "__main__":
    main()