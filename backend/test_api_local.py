"""
Local API Verification Script
=============================
Tests all FastAPI endpoints for the Smart Agriculture Assistant backend.
Can be run:
1. Against an active local server at http://127.0.0.1:8000
2. In-process using FastAPI TestClient if the server is not currently running.
"""

import os
import sys
import io
import time
import requests
from PIL import Image

# Force UTF-8 encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8000")


def get_test_client_or_requests():
    """
    Check if a server is listening on BASE_URL. If so, return a requests-based caller.
    Otherwise, instantiate FastAPI TestClient in-process.
    """
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=1.5)
        if r.status_code == 200:
            print(f"[✓] Connected to live backend at {BASE_URL}\n")
            return "live", None
    except Exception:
        pass

    print(f"[*] No server active on {BASE_URL}. Running in-process with FastAPI TestClient...\n")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from fastapi.testclient import TestClient
    from main import app
    return "in_process", TestClient(app)


MODE, CLIENT = get_test_client_or_requests()


def api_get(endpoint: str):
    if MODE == "live":
        return requests.get(f"{BASE_URL}{endpoint}")
    return CLIENT.get(endpoint)


def api_post(endpoint: str, json=None, files=None, data=None, headers=None):
    if MODE == "live":
        return requests.post(f"{BASE_URL}{endpoint}", json=json, files=files, data=data, headers=headers)
    return CLIENT.post(endpoint, json=json, files=files, data=data, headers=headers)


def test_health():
    print("=" * 60)
    print("TEST 1: GET /health")
    print("=" * 60)
    res = api_get("/health")
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.json()}\n")
    assert res.status_code == 200
    assert res.json().get("status") == "ok"
    assert "disease_module" in res.json()
    print(">>> TEST 1 RESULT: PASSED\n")


def test_disease_health():
    print("=" * 60)
    print("TEST 2: GET /api/disease/health")
    print("=" * 60)
    res = api_get("/api/disease/health")
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.json()}\n")
    assert res.status_code == 200
    data = res.json().get("data", {})
    assert data.get("supported_crops_count") == 13
    assert "confidence_threshold" in data
    print(">>> TEST 2 RESULT: PASSED\n")


def test_crop_prediction():
    print("=" * 60)
    print("TEST 3: POST /api/crop/predict")
    print("=" * 60)
    payload = {
        "nitrogen": 90,
        "phosphorus": 42,
        "potassium": 43,
        "temperature": 20.8,
        "humidity": 82.0,
        "ph": 6.5,
        "rainfall": 202.0
    }
    print(f"Payload: {payload}")
    res = api_post("/api/crop/predict", json=payload)
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.json()}\n")
    assert res.status_code == 200
    data = res.json().get("data", {})
    assert "recommended_crop" in data
    print(f">>> Recommended Crop: {data['recommended_crop']} ({data['confidence']}%)")
    print(">>> TEST 3 RESULT: PASSED\n")


def test_disease_crops_list():
    print("=" * 60)
    print("TEST 4: GET /api/disease/crops")
    print("=" * 60)
    res = api_get("/api/disease/crops")
    print(f"Status Code: {res.status_code}")
    crops = res.json().get("crops", [])
    print(f"Supported Crops ({len(crops)}): {[c['name'] for c in crops]}\n")
    assert res.status_code == 200
    assert len(crops) == 13
    print(">>> TEST 4 RESULT: PASSED\n")


def test_disease_prediction():
    print("=" * 60)
    print("TEST 5: POST /api/disease/predict (Leaf Image Diagnosis)")
    print("=" * 60)

    # Check for real test image in local repository first
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    real_sample_path = os.path.join(repo_root, "ml", "data", "plant", "apple", "Healthy leaf", "IMG_20190726_190843.jpg")

    if os.path.isfile(real_sample_path):
        print(f"Using real sample leaf image: {real_sample_path}")
        with open(real_sample_path, "rb") as f:
            img_bytes = f.read()
    else:
        print("Using synthetic green leaf image for diagnosis...")
        img = Image.new("RGB", (224, 224), color=(70, 140, 50))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        img_bytes = buf.getvalue()

    files = {"file": ("leaf.jpg", img_bytes, "image/jpeg")}
    data = {"crop_name": "apple"}

    res = api_post("/api/disease/predict", files=files, data=data)
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.json()}\n")
    assert res.status_code == 200
    pred = res.json().get("data", {})
    assert "disease" in pred
    assert "top_predictions" in pred
    assert "treatment" in pred
    print(f">>> Diagnosed Condition: {pred['plant']} — {pred['disease']}")
    print(f">>> Confidence Score  : {pred['confidence']}%")
    print(f">>> Is Healthy Flag   : {pred['is_healthy']}")
    print(f">>> Top 3 Candidates  : {pred['top_predictions']}")
    print(f">>> Treatment Advice  : {list(pred['treatment'].keys())}")
    print(">>> TEST 5 RESULT: PASSED\n")


def test_chat_endpoints():
    print("=" * 60)
    print("TEST 6: POST /api/chat (Farming Assistant)")
    print("=" * 60)
    payload = {
        "message": "What is the optimal soil pH for growing wheat?",
        "history": []
    }
    headers = {"Authorization": "Bearer jalsaathi-local-demo-farmer"}
    res = api_post("/api/chat", json=payload, headers=headers)
    print(f"Status Code: {res.status_code}")
    reply = res.json().get("reply", "")
    print(f"Reply: {reply[:150]}...\n")
    assert res.status_code == 200
    print(">>> TEST 6 RESULT: PASSED\n")


def run_all():
    print("============================================================")
    print("     STARTING SMART AGRICULTURE BACKEND API VERIFICATION     ")
    print("============================================================\n")

    test_health()
    test_disease_health()
    test_crop_prediction()
    test_disease_crops_list()
    test_disease_prediction()
    test_chat_endpoints()

    print("============================================================")
    print("           ALL BACKEND API ENDPOINTS VERIFIED!              ")
    print("============================================================\n")


if __name__ == "__main__":
    run_all()
