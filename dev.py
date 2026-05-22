import os
import sys
import subprocess

# 1. Force execution inside the virtual environment if it exists to avoid dependency/ImportError issues
def check_and_relaunch_in_venv():
    # Detect virtual environment python
    venv_python = os.path.join("venv", "Scripts", "python.exe") if os.name == "nt" else os.path.join("venv", "bin", "python")
    
    if os.path.exists(venv_python):
        current_exe = os.path.abspath(sys.executable)
        target_exe = os.path.abspath(venv_python)
        if current_exe != target_exe:
            print(f"[info] Automatically re-launching inside virtual environment ({venv_python})...")
            # Forward all command line arguments
            try:
                result = subprocess.run([venv_python] + sys.argv)
                sys.exit(result.returncode)
            except Exception as e:
                print(f"[warning] Failed to re-launch in venv: {e}")
                sys.exit(1)

check_and_relaunch_in_venv()

# 2. Safe to import dependencies now that we are running inside the virtual environment
import requests
from dotenv import load_dotenv

def print_banner(text):
    print("=" * 60)
    print(f" {text}")
    print("=" * 60)

def check_serper_key():
    load_dotenv(override=True)
    key = os.getenv("SERPER_API_KEY")
    if not key:
        print("[error] WARNING: SERPER_API_KEY is not set in your .env file!")
        print("Please create a .env file and set SERPER_API_KEY=your_key_here")
        print("=" * 60)
        return False
    # Simple sanity check: length or pattern could be added, but we just verify it's non‑empty
    print("[ok] SERPER_API_KEY validated successfully!")
    return True

def check_gemini_key():
    load_dotenv(override=True)
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("[error] WARNING: GEMINI_API_KEY is not set in your .env file!")
        print("Please create a .env file and set GEMINI_API_KEY=your_key_here")
        print("=" * 60)
        return False
        
    try:
        # Perform a lightweight API check
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 403:
            resp_json = resp.json()
            error_msg = resp_json.get("error", {}).get("message", "")
            if "leaked" in error_msg.lower():
                print("[error] ERROR: Your GEMINI_API_KEY has been BLOCKED/REVOKED by Google because it was leaked!")
                print("-> Please go to Google AI Studio (https://aistudio.google.com/) and generate a NEW API key.")
                print("-> Update the GEMINI_API_KEY in your '.env' file with the new key.")
                print("=" * 60)
                return False
            else:
                print(f"[error] WARNING: GEMINI_API_KEY returned a permission error (403): {error_msg}")
        elif resp.status_code == 400:
            print(f"[warning] WARNING: GEMINI_API_KEY validation returned status code 400. Check your key formatting.")
        elif resp.status_code == 200:
            print("[ok] GEMINI_API_KEY validated successfully!")
    except Exception as e:
        print(f"[warning] Could not validate GEMINI_API_KEY online: {e}")
    return True

def run_ingest():
    print_banner("RUNNING DOCUMENT INGESTION PIPELINE")
    subprocess.run([sys.executable, "-m", "src.ingest"])

def run_api():
    print_banner("STARTING FASTAPI BACKEND SERVER")
    # Validate both API keys before starting the server
    if not check_gemini_key() or not check_serper_key():
        print("[error] Missing required API keys. Exiting.")
        sys.exit(1)
    print("Access the API docs at: http://localhost:8000/docs")
    subprocess.run([sys.executable, "-m", "uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"])

def run_ui():
    print_banner("STARTING GRADIO STUNNING FRONTEND UI")
    # Validate both API keys before starting the UI
    if not check_gemini_key() or not check_serper_key():
        print("[error] Missing required API keys. Exiting.")
        sys.exit(1)
    
    print("Access the interactive web UI at: http://localhost:7860")
    subprocess.run([sys.executable, "-m", "src.app"])

if __name__ == "__main__":
    if not os.path.exists("vector_store"):
        print("Vector database 'vector_store' not found. Ingesting default documents first...")
        run_ingest()

    args = sys.argv[1:]
    if not args or args[0] == "ui":
        run_ui()
    elif args[0] == "api":
        run_api()
    elif args[0] == "ingest":
        run_ingest()
    else:
        print("Usage:")
        print("  python dev.py ui       - Run the Gradio Web UI (Default)")
        print("  python dev.py api      - Run the FastAPI backend server")
        print("  python dev.py ingest   - Run the document ingestion pipeline")
