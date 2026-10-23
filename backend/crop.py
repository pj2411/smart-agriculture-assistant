"""
Crop Recommendation Service
Loads the pre-trained CatBoost model and scaler to recommend crops.
"""

import os
import pickle
import numpy as np
import pandas as pd

# Path to trained crop model artifacts
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "crop_model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "models", "crop_scaler.pkl")

# In-memory cached model and scaler
_crop_model = None
_crop_scaler = None


def load_artifacts():
    """Load model and scaler once and keep them in memory."""
    global _crop_model, _crop_scaler
    if _crop_model is None or _crop_scaler is None:
        with open(MODEL_PATH, "rb") as f:
            _crop_model = pickle.load(f)
        with open(SCALER_PATH, "rb") as f:
            _crop_scaler = pickle.load(f)
    return _crop_model, _crop_scaler


def predict_crop(
    nitrogen: float,
    phosphorus: float,
    potassium: float,
    temperature: float,
    humidity: float,
    ph: float,
    rainfall: float
) -> dict:
    """
    Predict optimal crop based on soil and weather parameters.
    Returns recommended crop name and confidence percentage.
    """
    model, scaler = load_artifacts()

    # Format input data
    input_data = pd.DataFrame([[
        nitrogen, phosphorus, potassium,
        temperature, humidity, ph, rainfall
    ]], columns=["N", "P", "K", "temperature", "humidity", "ph", "rainfall"])

    # Scale inputs and predict
    scaled_input = scaler.transform(input_data)
    prediction = model.predict(scaled_input)
    crop_name = str(np.asarray(prediction).ravel()[0])

    # Calculate prediction confidence
    confidence = 0.0
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(scaled_input)
        confidence = float(np.max(probabilities)) * 100.0

    return {
        "recommended_crop": crop_name,
        "confidence": round(confidence, 2)
    }
