from pathlib import Path
import pickle

import numpy as np
import pandas as pd
import tensorflow as tf

from PIL import Image
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_DIR = PROJECT_ROOT / "data" / "plant"

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp"
}

IMAGE_SIZE = (224, 224)

BATCH_SIZE = 32

RANDOM_STATE = 42


# ============================================================
# COLLECT IMAGE FILES
# ============================================================

def collect_image_files(dataset_dir):
    """
    Recursively collect all image files from the
    plant disease datasets.

    Images inside the quarantine folder are excluded.
    """

    image_files = []

    for path in dataset_dir.rglob("*"):

        if not path.is_file():
            continue

        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        relative_path = path.relative_to(dataset_dir)

        # Exclude quarantined images
        if (
            relative_path.parts
            and relative_path.parts[0].lower() == "quarantine"
        ):
            continue

        image_files.append(path)

    return image_files


image_files = collect_image_files(DATASET_DIR)


# ============================================================
# DATASET AND CLASS IDENTIFICATION
# ============================================================

def get_dataset_name(image_path):
    """
    Return the top-level dataset name.
    """

    relative_path = image_path.relative_to(DATASET_DIR)

    return relative_path.parts[0]


def get_class_name(image_path):
    """
    Return the immediate parent directory name,
    which represents the disease class.
    """

    return image_path.parent.name


# ============================================================
# CREATE IMAGE METADATA
# ============================================================

records = []

for image_path in image_files:

    records.append({
        "Path": str(image_path),
        "Dataset": get_dataset_name(image_path),
        "Class": get_class_name(image_path)
    })


disease_df = pd.DataFrame(records)


# ============================================================
# EXCLUDE DATASETS WITHOUT VALID DISEASE LABELS
# ============================================================

# Lentil contains images without disease-specific
# class folders and therefore cannot be directly used
# for supervised disease classification.

EXCLUDED_DATASETS = {
    "lentil"
}

disease_df = disease_df[
    ~disease_df["Dataset"].isin(EXCLUDED_DATASETS)
].copy()


# ============================================================
# DETECT EXISTING TRAIN / VALIDATION / TEST SPLITS
# ============================================================

SPLIT_NAMES = {
    "train",
    "test",
    "val",
    "validation"
}


def detect_split(image_path):
    """
    Detect whether an image already belongs to
    train, validation, or test.
    """

    relative_path = image_path.relative_to(DATASET_DIR)

    parts = [
        part.lower()
        for part in relative_path.parts
    ]

    for split in SPLIT_NAMES:

        if split in parts:

            if split == "validation":
                return "val"

            return split

    return "unspecified"


disease_df["Split"] = disease_df["Path"].apply(
    lambda x: detect_split(Path(x))
)


# ============================================================
# STRATIFIED SPLITTING
# ============================================================

def split_unspecified_dataset(df):
    """
    Split a dataset without predefined splits into:

        70% Training
        15% Validation
        15% Testing

    Stratification is used to preserve class proportions.
    """

    train_df, temp_df = train_test_split(
        df,
        test_size=0.30,
        stratify=df["Class"],
        random_state=RANDOM_STATE
    )

    val_df, test_df = train_test_split(
        temp_df,
        test_size=0.50,
        stratify=temp_df["Class"],
        random_state=RANDOM_STATE
    )

    train_df = train_df.copy()
    val_df = val_df.copy()
    test_df = test_df.copy()

    train_df["Split"] = "train"
    val_df["Split"] = "val"
    test_df["Split"] = "test"

    return pd.concat(
        [
            train_df,
            val_df,
            test_df
        ],
        ignore_index=True
    )


final_split_parts = []


# ============================================================
# DATASETS WITHOUT PREDEFINED SPLITS
# ============================================================

# Rice is handled separately because it contains
# predefined training and validation folders.

unspecified_datasets = (
    disease_df.loc[
        disease_df["Split"] == "unspecified",
        "Dataset"
    ]
    .unique()
)

unspecified_datasets = [
    dataset
    for dataset in unspecified_datasets
    if dataset != "rice"
]


for dataset_name in unspecified_datasets:

    dataset_df = disease_df[
        (disease_df["Dataset"] == dataset_name) &
        (disease_df["Split"] == "unspecified")
    ].copy()

    split_df = split_unspecified_dataset(
        dataset_df
    )

    final_split_parts.append(
        split_df
    )


# ============================================================
# PLANTWILD
# ============================================================

# PlantWild already contains predefined
# train / validation / test folders.
#
# These original splits are preserved.

plantwild_df = disease_df[
    disease_df["Dataset"] == "plant wild"
].copy()

final_split_parts.append(
    plantwild_df
)


# ============================================================
# ORANGE
# ============================================================

# Orange contains predefined train/test folders.
#
# The existing training set is divided into:
#
#     85% training
#     15% validation
#
# The existing test set is preserved.

orange_train = disease_df[
    (disease_df["Dataset"] == "orange") &
    (disease_df["Split"] == "train")
].copy()

orange_test = disease_df[
    (disease_df["Dataset"] == "orange") &
    (disease_df["Split"] == "test")
].copy()


orange_train, orange_val = train_test_split(
    orange_train,
    test_size=0.15,
    stratify=orange_train["Class"],
    random_state=RANDOM_STATE
)


orange_train["Split"] = "train"
orange_val["Split"] = "val"
orange_test["Split"] = "test"


final_split_parts.extend([
    orange_train,
    orange_val,
    orange_test
])


# ============================================================
# RICE
# ============================================================

# Rice contains:
#
#     predefined training data
#     predefined validation data
#     remaining unspecified images
#
# Existing train/validation data are preserved.
# Remaining unspecified images are assigned to test.

rice_train = disease_df[
    (disease_df["Dataset"] == "rice") &
    (disease_df["Split"] == "train")
].copy()

rice_val = disease_df[
    (disease_df["Dataset"] == "rice") &
    (disease_df["Split"] == "val")
].copy()

rice_test = disease_df[
    (disease_df["Dataset"] == "rice") &
    (disease_df["Split"] == "unspecified")
].copy()


rice_train["Split"] = "train"
rice_val["Split"] = "val"
rice_test["Split"] = "test"


final_split_parts.extend([
    rice_train,
    rice_val,
    rice_test
])


# ============================================================
# COMBINE FINAL DATASET
# ============================================================

final_disease_df = pd.concat(
    final_split_parts,
    ignore_index=True
)


final_disease_df = final_disease_df[
    [
        "Path",
        "Dataset",
        "Class",
        "Split"
    ]
].copy()


# ============================================================
# DATASET-SPECIFIC LABEL ENCODING
# ============================================================

# Each dataset has its own disease classes.
#
# Therefore, a separate LabelEncoder is created
# and saved for every dataset.

LABEL_ENCODER_DIR = (
    PROJECT_ROOT /
    "models" /
    "disease_label_encoders"
)

LABEL_ENCODER_DIR.mkdir(
    parents=True,
    exist_ok=True
)


for dataset_name in sorted(
    final_disease_df["Dataset"].unique()
):

    dataset_classes = sorted(
        final_disease_df.loc[
            final_disease_df["Dataset"] == dataset_name,
            "Class"
        ].unique()
    )

    encoder = LabelEncoder()

    encoder.fit(
        dataset_classes
    )

    mask = (
        final_disease_df["Dataset"]
        == dataset_name
    )

    final_disease_df.loc[
        mask,
        "Label"
    ] = encoder.transform(
        final_disease_df.loc[
            mask,
            "Class"
        ]
    )

    encoder_filename = (
        f"{dataset_name.replace(' ', '_')}"
        "_label_encoder.pkl"
    )

    encoder_path = (
        LABEL_ENCODER_DIR /
        encoder_filename
    )

    with open(
        encoder_path,
        "wb"
    ) as file:

        pickle.dump(
            encoder,
            file
        )


# Convert labels to integer
final_disease_df["Label"] = (
    final_disease_df["Label"]
    .astype(int)
)


# ============================================================
# IMAGE LOADING AND PREPROCESSING
# ============================================================

def load_and_preprocess_image(image_path):
    """
    Load and preprocess an image.

    Processing steps:

        1. Open image
        2. Convert to RGB
        3. Resize to 224 x 224
        4. Convert to float32
        5. Normalize pixel values to [0, 1]
    """

    try:

        image = Image.open(
            image_path
        )

        # Convert grayscale/RGBA/etc. to RGB
        image = image.convert(
            "RGB"
        )

        # Resize all images to a fixed size
        image = image.resize(
            IMAGE_SIZE,
            Image.Resampling.BILINEAR
        )

        # Convert to NumPy array
        image = np.asarray(
            image,
            dtype=np.float32
        )

        # Normalize pixels
        image /= 255.0

        return image

    except Exception as error:

        print(
            f"Error processing image: "
            f"{image_path}\n"
            f"{error}"
        )

        return None


# ============================================================
# DATA AUGMENTATION
# ============================================================

# Augmentation is applied ONLY to training images.
#
# Validation and test images are NOT augmented.
#
# This helps the model generalize to variations in:
#     - orientation
#     - rotation
#     - zoom
#     - contrast

data_augmentation = tf.keras.Sequential(
    [
        tf.keras.layers.RandomFlip(
            mode="horizontal"
        ),

        tf.keras.layers.RandomRotation(
            factor=0.10
        ),

        tf.keras.layers.RandomZoom(
            height_factor=0.10,
            width_factor=0.10
        ),

        tf.keras.layers.RandomContrast(
            factor=0.10
        )
    ],
    name="disease_data_augmentation"
)


# ============================================================
# TENSORFLOW DATASET GENERATOR
# ============================================================

def tensorflow_dataset_generator(
    dataframe,
    shuffle=False
):
    """
    Generate:

        image
        label
        dataset name

    from the metadata dataframe.
    """

    data = dataframe.copy()

    if shuffle:

        data = data.sample(
            frac=1,
            random_state=RANDOM_STATE
        ).reset_index(
            drop=True
        )

    for _, row in data.iterrows():

        image = load_and_preprocess_image(
            row["Path"]
        )

        # Skip unreadable/corrupt images
        if image is None:
            continue

        label = np.int32(
            row["Label"]
        )

        dataset_name = (
            row["Dataset"]
            .encode("utf-8")
        )

        yield (
            image,
            label,
            dataset_name
        )


# ============================================================
# TENSORFLOW OUTPUT SIGNATURE
# ============================================================

OUTPUT_SIGNATURE = (
    tf.TensorSpec(
        shape=(224, 224, 3),
        dtype=tf.float32
    ),

    tf.TensorSpec(
        shape=(),
        dtype=tf.int32
    ),

    tf.TensorSpec(
        shape=(),
        dtype=tf.string
    )
)


# ============================================================
# CREATE TENSORFLOW DATASET
# ============================================================

def create_tf_dataset(
    dataframe,
    shuffle=False,
    augment=False
):
    """
    Create a TensorFlow input pipeline.

    Steps:

        Image loading
            ↓
        Resize
            ↓
        Normalization
            ↓
        Optional augmentation
            ↓
        Batching
            ↓
        Prefetching
    """

    dataset = tf.data.Dataset.from_generator(
        lambda: tensorflow_dataset_generator(
            dataframe,
            shuffle=shuffle
        ),
        output_signature=OUTPUT_SIGNATURE
    )

    # Apply augmentation only when requested.
    if augment:

        def augment_image(
            image,
            label,
            dataset_name
        ):

            image = data_augmentation(
                image,
                training=True
            )

            return (
                image,
                label,
                dataset_name
            )

        dataset = dataset.map(
            augment_image,
            num_parallel_calls=tf.data.AUTOTUNE
        )

    # Batch images
    dataset = dataset.batch(
        BATCH_SIZE
    )

    # Improve input pipeline performance
    dataset = dataset.prefetch(
        tf.data.AUTOTUNE
    )

    return dataset


# ============================================================
# CREATE TRAIN / VALIDATION / TEST DATAFRAMES
# ============================================================

train_df = final_disease_df[
    final_disease_df["Split"] == "train"
].copy()

val_df = final_disease_df[
    final_disease_df["Split"] == "val"
].copy()

test_df = final_disease_df[
    final_disease_df["Split"] == "test"
].copy()


# ============================================================
# CREATE FINAL TENSORFLOW DATASETS
# ============================================================

# Training:
#     shuffle = True
#     augmentation = True

train_tf_dataset = create_tf_dataset(
    train_df,
    shuffle=True,
    augment=True
)


# Validation:
#     shuffle = False
#     augmentation = False

val_tf_dataset = create_tf_dataset(
    val_df,
    shuffle=False,
    augment=False
)


# Testing:
#     shuffle = False
#     augmentation = False

test_tf_dataset = create_tf_dataset(
    test_df,
    shuffle=False,
    augment=False
)


# ============================================================
# SAVE FINAL METADATA
# ============================================================

METADATA_PATH = (
    PROJECT_ROOT /
    "reports" /
    "results" /
    "disease_final_metadata.csv"
)

METADATA_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)


final_disease_df.to_csv(
    METADATA_PATH,
    index=False
)


# ============================================================
# FINAL DATASET INFORMATION
# ============================================================

print()
print("=" * 60)
print("DISEASE PREPROCESSING COMPLETED")
print("=" * 60)

print(
    f"Total images       : {len(final_disease_df)}"
)

print(
    f"Training images    : {len(train_df)}"
)

print(
    f"Validation images  : {len(val_df)}"
)

print(
    f"Testing images     : {len(test_df)}"
)

print(
    f"Total datasets     : "
    f"{final_disease_df['Dataset'].nunique()}"
)

print(
    f"Total classes      : "
    f"{final_disease_df['Class'].nunique()}"
)

print()
print(
    "Image size         : 224 x 224"
)

print(
    "Normalization      : Pixel values / 255"
)

print(
    "Augmentation       : Training only"
)

print(
    "Batch size         : 32"
)

print()
print(
    f"Label encoders     : {LABEL_ENCODER_DIR}"
)

print(
    f"Metadata file      : {METADATA_PATH}"
)

print("=" * 60)