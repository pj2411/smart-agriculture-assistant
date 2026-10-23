"""
Upload Deep Learning models for Smart Agriculture Assistant to Hugging Face Hub.
"""

import os
import sys
from huggingface_hub import HfApi, login

REPO_ID = "DhruvKatharotiya/smart-agriculture-models"
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(ROOT_DIR, "backend", "models", "disease")

ACTIVE_MODELS = [
    "rice_resnet50_finetuned.keras",               # Upload rice first for fast verification
    "apple_resnet50_finetuned.keras",
    "black_gram_leaf_resnet50_finetuned.keras",
    "coconut_resnet50_finetuned.keras",
    "coffee_resnet50_finetuned.keras",
    "grapes_resnet50_finetuned.keras",
    "jute_resnet50_finetuned.keras",
    "maize_resnet50_finetuned.keras",
    "mango_resnet50_finetuned_best.keras",
    "orange_resnet50_finetuned.keras",
    "pigonpea_resnet50_finetuned.keras",
    "plant_wild_resnet50_finetuned.keras",
    "watermelon_resnet50_finetuned.keras",
]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 65)
    print("🌾 Smart Agriculture Assistant - Hugging Face Model Uploader")
    print("=" * 65)

    # 1. Obtain token
    token = None
    if len(sys.argv) > 1:
        token = sys.argv[1].strip()
    else:
        token = input("Enter your Hugging Face Access Token (starts with 'hf_...'): ").strip()

    if not token or not token.startswith("hf_"):
        print("\n[ERROR] Invalid token format!")
        print("Note: Do NOT enter the name/label of the token (e.g. 'Agriculture').")
        print("Instead, copy the secret token string itself (starts with 'hf_...').")
        print("You can copy it here: https://huggingface.co/settings/tokens\n")
        sys.exit(1)

    print("\n[*] Authenticating with Hugging Face...")
    try:
        login(token=token, add_to_git_credential=False)
        api = HfApi(token=token)
        user_info = api.whoami()
        username = user_info.get("name", "DhruvKatharotiya")
        print(f"[✓] Logged in successfully as: {username}")
    except Exception as e:
        print(f"[ERROR] Login failed: {e}")
        sys.exit(1)

    repo_id = f"{username}/smart-agriculture-models"

    # 2. Ensure repository exists
    print(f"\n[*] Ensuring model repository '{repo_id}' exists...")
    try:
        api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True, private=False)
        print(f"[✓] Model repository is ready: https://huggingface.co/{repo_id}")
    except Exception as e:
        print(f"[ERROR] Could not create/verify repo '{repo_id}': {e}")
        sys.exit(1)

    # 3. Upload active models
    print(f"\n[*] Found {len(ACTIVE_MODELS)} production models to upload.")
    print("    Starting upload into repository folder 'disease/'...\n")

    for idx, model_name in enumerate(ACTIVE_MODELS, 1):
        file_path = os.path.join(MODELS_DIR, model_name)
        if not os.path.isfile(file_path):
            print(f"[{idx}/{len(ACTIVE_MODELS)}] ⚠️ Missing local file: {model_name}, skipping.")
            continue

        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        print(f"[{idx}/{len(ACTIVE_MODELS)}] ⬆️ Uploading {model_name} ({size_mb:.1f} MB)...")
        try:
            api.upload_file(
                path_or_fileobj=file_path,
                path_in_repo=f"disease/{model_name}",
                repo_id=repo_id,
                repo_type="model"
            )
            print(f"[{idx}/{len(ACTIVE_MODELS)}] ✓ Uploaded {model_name}")
        except Exception as e:
            print(f"[{idx}/{len(ACTIVE_MODELS)}] ❌ Failed to upload {model_name}: {e}")

    print("\n" + "=" * 65)
    print("✨ Upload complete!")
    print(f"Model repo URL: https://huggingface.co/{repo_id}")
    print("\n👉 Next Step for Render:")
    print("1. Go to your Render Dashboard -> smart-agriculture-backend -> Environment")
    print(f"2. Add/Update Environment Variable:")
    print(f"   HF_REPO_ID = {repo_id}")
    print("=" * 65)


if __name__ == "__main__":
    main()
