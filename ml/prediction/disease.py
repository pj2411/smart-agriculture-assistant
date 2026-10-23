"""
Plant Disease Detection - Offline CLI Prediction Tool
=====================================================
Performs disease diagnosis on a local plant leaf image using trained ResNet50 models.
Applies exact training preprocessing (RGB conversion, 224x224 resize, /255.0 normalization).
"""

import os
import pickle
from pathlib import Path
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.applications.resnet50 import preprocess_input

# ------------------------------------------------------------
# Project paths (dynamic resolution)
# ------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = os.path.join(PROJECT_ROOT, "backend", "models", "disease")
ENCODER_DIR = os.path.join(PROJECT_ROOT, "backend", "models", "disease_label_encoders")

IMAGE_SIZE = (224, 224)
CONFIDENCE_THRESHOLD = 0.60

DATASET_CONFIG = {
    "apple": {
        "model": "apple_resnet50_finetuned.keras",
        "encoder": "apple_label_encoder.pkl"
    },
    "black_gram_leaf": {
        "model": "black_gram_leaf_resnet50_finetuned.keras",
        "encoder": "Black_Gram_Leaf_label_encoder.pkl"
    },
    "coconut": {
        "model": "coconut_resnet50_finetuned.keras",
        "encoder": "Coconut_label_encoder.pkl"
    },
    "coffee": {
        "model": "coffee_resnet50_finetuned.keras",
        "encoder": "coffee_label_encoder.pkl"
    },
    "grapes": {
        "model": "grapes_resnet50_finetuned.keras",
        "encoder": "grapes_label_encoder.pkl"
    },
    "jute": {
        "model": "jute_resnet50_finetuned.keras",
        "encoder": "jute_label_encoder.pkl"
    },
    "maize": {
        "model": "maize_resnet50_finetuned.keras",
        "encoder": "maize_label_encoder.pkl"
    },
    "mango": {
        "model": "mango_resnet50_finetuned_best.keras",
        "encoder": "mango_label_encoder.pkl"
    },
    "orange": {
        "model": "orange_resnet50_finetuned.keras",
        "encoder": "orange_label_encoder.pkl"
    },
    "pigonpea": {
        "model": "pigonpea_resnet50_finetuned.keras",
        "encoder": "pigonpea_label_encoder.pkl"
    },
    "plant_wild": {
        "model": "plant_wild_resnet50_finetuned.keras",
        "encoder": "plant_wild_label_encoder.pkl"
    },
    "rice": {
        "model": "rice_resnet50_finetuned.keras",
        "encoder": "rice_label_encoder.pkl"
    },
    "watermelon": {
        "model": "watermelon_resnet50_finetuned.keras",
        "encoder": "Watermelon_label_encoder.pkl"
    }
}


def run_prediction():
    image_path = input("\nEnter the path of the plant leaf image: ").strip().strip('"')

    if not os.path.isfile(image_path):
        print(f"\nError: Image file not found: {image_path}")
        return

    print("\nAvailable plant datasets:")
    for dataset in DATASET_CONFIG:
        print(f" - {dataset}")

    dataset_name = input("\nEnter the dataset/plant name: ").strip().lower()
    if dataset_name not in DATASET_CONFIG:
        print(f"\nError: Unsupported dataset '{dataset_name}'.")
        return

    model_path = os.path.join(MODEL_DIR, DATASET_CONFIG[dataset_name]["model"])
    encoder_path = os.path.join(ENCODER_DIR, DATASET_CONFIG[dataset_name]["encoder"])

    if not os.path.isfile(model_path):
        print(f"\nError: Model file not found at {model_path}")
        return

    if not os.path.isfile(encoder_path):
        print(f"\nError: Label encoder not found at {encoder_path}")
        return

    print("\nLoading ResNet50 model...")
    model = keras.models.load_model(
        model_path,
        compile=False,
        safe_mode=False,
        custom_objects={"preprocess_input": preprocess_input}
    )

    print("Loading label encoder...")
    with open(encoder_path, "rb") as file:
        label_encoder = pickle.load(file)

    # Load and preprocess image matching training
    image = tf.keras.utils.load_img(image_path, target_size=IMAGE_SIZE)
    image = tf.keras.utils.img_to_array(image)

    # CRUCIAL: Normalize to [0, 1] range by dividing by 255.0.
    # The model has internal `layers.Rescaling(scale=255.0)` before ResNet50 preprocessing.
    image = image.astype(np.float32) / 255.0
    image = np.expand_dims(image, axis=0)

    print("Running disease inference...")
    raw_predictions = model.predict(image, verbose=0)[0]

    # Top-3 predictions
    classes = label_encoder.classes_
    top_indices = np.argsort(raw_predictions)[::-1][:min(3, len(classes))]

    print("\n" + "=" * 55)
    print("           PLANT DISEASE PREDICTION RESULT")
    print("=" * 55)
    print(f"Plant Species : {dataset_name.replace('_', ' ').title()}")

    best_idx = top_indices[0]
    best_conf = float(raw_predictions[best_idx])
    best_class = str(classes[best_idx])

    if best_conf < CONFIDENCE_THRESHOLD:
        print(f"Diagnosis     : Uncertain - please upload a clearer leaf image")
        print(f"Status        : Top prediction confidence ({best_conf*100:.1f}%) < {CONFIDENCE_THRESHOLD*100:.0f}% threshold")
    else:
        print(f"Diagnosis     : {best_class}")
        print(f"Confidence    : {best_conf * 100:.2f}%")

    print("\nTop Candidate Predictions:")
    for rank, idx in enumerate(top_indices, 1):
        print(f" {rank}. {classes[idx]:<30} {raw_predictions[idx]*100:>6.2f}%")

    print("=" * 55 + "\n")


if __name__ == "__main__":
    run_prediction()