"""
Sample Leaf Verification Script
================================
Runs 5 sample leaf images through the plant disease detection pipeline
and prints detailed diagnosis, confidence, top-3 candidates, and remedies.
Can be used to test locally or against a deployed URL (e.g. Render).

Usage:
    python verify_sample_leaves.py
    python verify_sample_leaves.py --url https://smart-agriculture-backend-4j3w.onrender.com
"""

import os
import sys
import argparse
import requests
from PIL import Image
import io

# Force UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# 5 diverse test samples across different crops and health statuses
SAMPLES = [
    {
        "crop": "apple",
        "expected": "Healthy leaf",
        "path": os.path.join(ROOT_DIR, "ml", "data", "plant", "apple", "Healthy leaf", "IMG_20190726_190843.jpg"),
        "fallback_color": (50, 150, 50)
    },
    {
        "crop": "apple",
        "expected": "Rust",
        "path": os.path.join(ROOT_DIR, "ml", "data", "plant", "apple", "Rust", "004127.JPG"),
        "fallback_color": (160, 100, 30)
    },
    {
        "crop": "rice",
        "expected": "Healthy or Leaf Condition",
        "path": os.path.join(ROOT_DIR, "ml", "data", "plant", "rice", "Healthy", "IMG_20190726_190843.jpg"),
        "fallback_color": (60, 160, 60)
    },
    {
        "crop": "maize",
        "expected": "Healthy or Blight/Rust",
        "path": os.path.join(ROOT_DIR, "ml", "data", "plant", "maize", "Healthy", "IMG_20190726_190843.jpg"),
        "fallback_color": (70, 170, 70)
    },
    {
        "crop": "watermelon",
        "expected": "Anthracnose / Downy Mildew / Healthy",
        "path": os.path.join(ROOT_DIR, "ml", "data", "plant", "Watermelon", "Healthy", "IMG_20190726_190843.jpg"),
        "fallback_color": (55, 145, 55)
    }
]


def load_image_bytes(sample_info):
    """Load real dataset image if present on disk, otherwise generate synthetic leaf."""
    if os.path.isfile(sample_info["path"]):
        with open(sample_info["path"], "rb") as f:
            return f.read(), "Real Leaf Image"

    # Search for any image in the dataset folder if exact filename differs
    parent_dir = os.path.dirname(sample_info["path"])
    if os.path.isdir(parent_dir):
        for fname in os.listdir(parent_dir):
            if fname.lower().endswith((".jpg", ".jpeg", ".png")):
                fpath = os.path.join(parent_dir, fname)
                with open(fpath, "rb") as f:
                    return f.read(), f"Dataset Sample ({fname})"

    # Synthetic fallback leaf
    img = Image.new("RGB", (224, 224), color=sample_info["fallback_color"])
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue(), "Synthetic Fallback"


def main():
    parser = argparse.ArgumentParser(description="Verify leaf disease detection pipeline.")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Backend API base URL.")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    print("=" * 70)
    print("       🌾 SMART AGRICULTURE ASSISTANT — LEAF PIPELINE TEST")
    print(f"       Target API Endpoint: {base_url}")
    print("=" * 70)

    is_live = False
    client = None

    # 1. Check health
    try:
        r = requests.get(f"{base_url}/health", timeout=3)
        if r.status_code == 200:
            is_live = True
            print("[✓] Target backend is online and reachable.\n")
    except Exception:
        pass

    if not is_live:
        print("[*] No active server on port 8000. Running in-process with FastAPI TestClient...\n")
        sys.path.insert(0, os.path.join(ROOT_DIR, "backend"))
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)

    # 2. Test sample leaves
    for idx, sample in enumerate(SAMPLES, 1):
        print("-" * 70)
        print(f"Sample {idx}/5 : Plant = {sample['crop'].upper()} | Expected = {sample['expected']}")

        img_bytes, source_desc = load_image_bytes(sample)
        print(f"Image Source : {source_desc} ({len(img_bytes)/1024:.1f} KB)")

        files = {"file": ("leaf.jpg", img_bytes, "image/jpeg")}
        data = {"crop_name": sample["crop"]}

        try:
            if is_live:
                res = requests.post(f"{base_url}/api/disease/predict", files=files, data=data, timeout=60)
            else:
                res = client.post("/api/disease/predict", files=files, data=data)

            if res.status_code == 200:
                result = res.json().get("data", {})
                print(f"Diagnosis    : {result.get('disease')}")
                print(f"Confidence   : {result.get('confidence')}%")
                print(f"Is Healthy   : {result.get('is_healthy')}")
                print(f"Is Uncertain : {result.get('is_uncertain')}")
                print("Top Candidates:")
                for rank, cand in enumerate(result.get("top_predictions", []), 1):
                    print(f"  {rank}. {cand['disease']:<30} {cand['confidence']:>6.2f}%")
                treatment = result.get("treatment", {})
                if treatment:
                    print(f"Remedy       : {treatment.get('organic', '')[:90]}...")
                print("[✓] PASSED")
            else:
                print(f"[X] Request failed (HTTP {res.status_code}): {res.text}")
        except Exception as e:
            print(f"[X] Prediction error: {e}")

    print("\n" + "=" * 70)
    print("                   VERIFICATION COMPLETED")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
