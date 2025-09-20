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
        # On Unix-like systems (like Hugging Face), os.kill is more reliable
        try:
            os.kill(bg_process.pid, signal.SIGTERM)
            bg_process.wait(timeout=5)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            print("⚠️ Force killing background process...")
            bg_process.kill()
        print("✅ Pipeline terminated.")


def run_command(command, description):
    """Runs a setup command and exits if it fails."""
    print(f"🚀 {description}...")
    # Use sys.executable to ensure we use the python from the correct venv
    result = subprocess.run([sys.executable, "-m", command], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ ERROR: {description} failed.")
        print(result.stderr)
        sys.exit(result.returncode)
    print(f"✅ {description} complete.")


def main():
    # Register the cleanup function to be called on any script exit
    atexit.register(cleanup)

    # Initialize and Seed
    run_command("database/database_setup.py", "Initializing database")
    run_command("scripts/seed_db.py", "Seeding initial data")

    # Start the background data pipeline
    print("📡 Starting background data pipeline...")
    global bg_process
    bg_process = subprocess.Popen([sys.executable, "main.py"])
    print(f"✅ Data pipeline started with PID: {bg_process.pid}")

    # Start the Streamlit app (this is the main blocking process)
    print("📊 Starting Streamlit dashboard...")

    subprocess.run(
        ["streamlit", "run", "app.py", "--server.port", "8501", "--server.headless", "true"]
    )


if __name__ == "__main__":
    main()