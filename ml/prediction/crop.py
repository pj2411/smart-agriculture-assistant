import pickle
import pandas as pd
import numpy as np


# Load trained model
with open("models/crop_model.pkl", "rb") as f:
    model = pickle.load(f)

# Load scaler
with open("models/crop_scaler.pkl", "rb") as f:
    scaler = pickle.load(f)

# Load label encoder
with open("models/crop_label_encoder.pkl", "rb") as f:
    label_encoder = pickle.load(f)


def predict_crop(
    nitrogen,
    phosphorus,
    potassium,
    temperature,
    humidity,
    ph,
    rainfall
):
    """
    Predict the most suitable crop based on
    soil and environmental conditions.
    """

    # Arrange input in the same order used during training
    input_data = pd.DataFrame([[
    nitrogen,
    phosphorus,
    potassium,
    temperature,
    humidity,
    ph,
    rainfall
    ]], columns=[
    "N",
    "P",
    "K",
    "temperature",
    "humidity",
    "ph",
    "rainfall"
])

    # Apply the same scaler used during training
    input_scaled = scaler.transform(input_data)

    # Predict encoded class
    prediction = model.predict(input_scaled)

    crop = np.asarray(prediction).ravel()[0]

    return crop


if __name__ == "__main__":

    crop = predict_crop(
        nitrogen=90,
        phosphorus=42,
        potassium=43,
        temperature=20.8,
        humidity=82,
        ph=6.5,
        rainfall=202
    )

    print("Recommended Crop:", crop)