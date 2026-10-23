"""JalSaathi local application runner."""

import os
import sys
import time
import subprocess
import webbrowser
import urllib.request

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")



def is_service_running(url: str) -> bool:
    """Check if an HTTP endpoint returns a response."""
    try:
        with urllib.request.urlopen(url, timeout=1.5) as res:
            return res.status == 200
    except Exception:
        return False


def main():
    print("=" * 60)
    print("🌾 JalSaathi")
    print("=" * 60)

    # Prefer python interpreter from the virtual environment if available
    venv_candidates = [
        os.path.join(ROOT_DIR, ".venv", "bin", "python"),
        os.path.join(ROOT_DIR, ".venv", "Scripts", "python.exe"),
    ]
    python_exe = next((path for path in venv_candidates if os.path.exists(path)), sys.executable)

    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    processes = []

    # 1. FastAPI Backend
    if is_service_running("http://127.0.0.1:8000/health"):
        print("[✓] Backend already running at http://127.0.0.1:8000")
    else:
        print("[*] Starting FastAPI Backend on http://127.0.0.1:8000 ...")
        backend_proc = subprocess.Popen(
            [python_exe, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
            cwd=BACKEND_DIR
        )
        processes.append(backend_proc)

    # 2. React + Vite Frontend
    if is_service_running("http://127.0.0.1:5173"):
        print("[✓] Frontend already running at http://127.0.0.1:5173")
    else:
        print("[*] Starting Vite Frontend on http://127.0.0.1:5173 ...")
        frontend_proc = subprocess.Popen(
            [npm_cmd, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"],
            cwd=FRONTEND_DIR
        )
        processes.append(frontend_proc)

    # 3. Wait for frontend to be ready
    print("\nConnecting to services...")
    for _ in range(15):
        if is_service_running("http://127.0.0.1:5173"):
            break
        time.sleep(1)

    print("\n" + "=" * 60)
    print("✨ JalSaathi is live!")
    print("🌐 Frontend Application : http://127.0.0.1:5173")
    print("🚀 Backend REST API      : http://127.0.0.1:8000")
    print("📚 Interactive API Docs : http://127.0.0.1:8000/docs")
    print("=" * 60)
    print("Press Ctrl+C to terminate services.\n")

    webbrowser.open("http://127.0.0.1:5173")

    if not processes:
        print("Both services were already running in the background.")
        return

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping services...")
        for proc in processes:
            proc.terminate()
        print("All services stopped.")


if __name__ == "__main__":
    main()
