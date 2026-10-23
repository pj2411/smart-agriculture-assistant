"""
Plant Disease Detection Service
================================
This module provides plant leaf disease diagnosis across 13 agricultural crop species
using deep transfer-learning models (ResNet50 architecture).

Key Features:
- Exact preprocessing pipeline matching model training (RGB conversion, 224x224 resize, /255.0 normalization).
- Thread-safe lazy loading with single-model caching to run within Render's 512 MB RAM limit.
- Automatic on-demand model download from Hugging Face Hub if missing locally.
- Confidence threshold evaluation (default 0.60): returns "Uncertain" if prediction is ambiguous.
- Top-3 candidate predictions with probability percentages.
- Comprehensive treatment, chemical/organic remedies, and prevention advice for all supported diseases.
- Diagnostic health check endpoint helper.
"""

import os
import gc
import pickle
import threading
import logging
import urllib.request
from io import BytesIO
from typing import Tuple, Dict, Any, List, Optional
import numpy as np

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("disease_service")

# Suppress noisy oneDNN and TensorFlow debug messages
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"


# ---------------------------------------------------------------------------
# Environment Variables and Directory Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Path where trained .keras models are stored locally
MODEL_DIR = os.getenv("MODEL_DIR", os.path.join(BASE_DIR, "models", "disease"))

# Path where trained scikit-learn LabelEncoder pickle files are stored
ENCODER_DIR = os.getenv("ENCODER_DIR", os.path.join(BASE_DIR, "models", "disease_label_encoders"))

# Hugging Face repository where disease models are hosted
DEFAULT_HF_REPO = "DhruvKatharotiya/smart-agriculture-models"
HF_REPO_ID = os.getenv("HF_REPO_ID", DEFAULT_HF_REPO).strip()

# Confidence threshold below which the model is considered uncertain (default: 0.60 = 60%)
CONFIDENCE_THRESHOLD = float(os.getenv("DISEASE_CONFIDENCE_THRESHOLD", "0.60"))

# Maximum allowed uploaded image size in bytes (default: 10 MB)
MAX_IMAGE_SIZE_BYTES = int(os.getenv("MAX_IMAGE_SIZE_BYTES", str(10 * 1024 * 1024)))

# Input dimensions expected by ResNet50
IMAGE_SIZE: Tuple[int, int] = (224, 224)


# ---------------------------------------------------------------------------
# Crop Configuration Mapping
# Defines model filename, label encoder filename, and display name for all 13 crops.
# Note: Filenames preserve exact case for Linux compatibility.
# ---------------------------------------------------------------------------
DATASET_CONFIG: Dict[str, Dict[str, str]] = {
    "apple": {
        "model": "apple_resnet50_finetuned.keras",
        "encoder": "apple_label_encoder.pkl",
        "name": "Apple"
    },
    "black_gram_leaf": {
        "model": "black_gram_leaf_resnet50_finetuned.keras",
        "encoder": "Black_Gram_Leaf_label_encoder.pkl",
        "name": "Black Gram"
    },
    "coconut": {
        "model": "coconut_resnet50_finetuned.keras",
        "encoder": "Coconut_label_encoder.pkl",
        "name": "Coconut"
    },
    "coffee": {
        "model": "coffee_resnet50_finetuned.keras",
        "encoder": "coffee_label_encoder.pkl",
        "name": "Coffee"
    },
    "grapes": {
        "model": "grapes_resnet50_finetuned.keras",
        "encoder": "grapes_label_encoder.pkl",
        "name": "Grapes"
    },
    "jute": {
        "model": "jute_resnet50_finetuned.keras",
        "encoder": "jute_label_encoder.pkl",
        "name": "Jute"
    },
    "maize": {
        "model": "maize_resnet50_finetuned.keras",
        "encoder": "maize_label_encoder.pkl",
        "name": "Maize"
    },
    "mango": {
        "model": "mango_resnet50_finetuned_best.keras",
        "encoder": "mango_label_encoder.pkl",
        "name": "Mango"
    },
    "orange": {
        "model": "orange_resnet50_finetuned.keras",
        "encoder": "orange_label_encoder.pkl",
        "name": "Orange"
    },
    "pigonpea": {
        "model": "pigonpea_resnet50_finetuned.keras",
        "encoder": "pigonpea_label_encoder.pkl",
        "name": "Pigeon Pea"
    },
    "plant_wild": {
        "model": "plant_wild_resnet50_finetuned.keras",
        "encoder": "plant_wild_label_encoder.pkl",
        "name": "Wild Plant"
    },
    "rice": {
        "model": "rice_resnet50_finetuned.keras",
        "encoder": "rice_label_encoder.pkl",
        "name": "Rice"
    },
    "watermelon": {
        "model": "watermelon_resnet50_finetuned.keras",
        "encoder": "Watermelon_label_encoder.pkl",
        "name": "Watermelon"
    }
}


# ---------------------------------------------------------------------------
# In-Memory Cache and Thread Synchronization
# Render Free Tier provides 512MB RAM. Holding 13 ResNet50 models simultaneously
# would require ~2.7 GB RAM and crash the container. Therefore, we keep only ONE
# active crop model in memory at any given time.
# ---------------------------------------------------------------------------
_model_lock = threading.Lock()
_current_crop: Optional[str] = None
_current_model: Any = None
_current_encoder: Any = None
_is_warming_up: bool = False


# ---------------------------------------------------------------------------
# Treatment and Prevention Advisory Knowledge Base
# Curated agronomic recommendations for conditions across all 13 supported plants.
# ---------------------------------------------------------------------------
TREATMENT_ADVISORY: Dict[str, Dict[str, Dict[str, str]]] = {
    "apple": {
        "Alternaria leaf spot": {
            "organic": "Spray copper-based fungicides or neem oil (0.5%) at early bud stage; prune lower foliage to improve air circulation.",
            "chemical": "Apply Mancozeb (2.5 g/L) or Iprodione spray upon first sign of lesions.",
            "prevention": "Rake and destroy fallen leaves in autumn; prune canopies to maximize sunlight penetration."
        },
        "Brown spot": {
            "organic": "Apply bio-fungicide Bacillus subtilis or bio-sulfur spray during humid periods.",
            "chemical": "Spray Chlorothalonil or Captan 50 WP according to local extension dosage.",
            "prevention": "Avoid overhead sprinkler irrigation; maintain adequate tree spacing and balanced potassium nutrition."
        },
        "Gray spot": {
            "organic": "Apply potassium bicarbonate spray (3 g/L) combined with light horticultural oil.",
            "chemical": "Apply systemic strobilurin fungicides (e.g. Pyraclostrobin or Kresoxim-methyl).",
            "prevention": "Prune out diseased twigs during dormancy; disinfect pruning shears with 70% alcohol."
        },
        "Rust": {
            "organic": "Dust with wettable sulfur early in the season before cedar gall spore release.",
            "chemical": "Apply Myclobutanil or Tebuconazole fungicide at tight cluster through petal fall.",
            "prevention": "Remove nearby wild juniper or cedar trees (alternate hosts) within a 500-meter radius."
        },
        "Healthy leaf": {
            "organic": "Maintain regular foliar compost tea and balanced organic mulch.",
            "chemical": "No chemical treatment required. Routine preventative monitoring is advised.",
            "prevention": "Continue regular pest scouting, balanced irrigation, and balanced NPK soil nutrition."
        }
    },
    "black_gram_leaf": {
        "Cercospora leaf spot": {
            "organic": "Spray neem seed kernel extract (NSKE 5%) or copper oxychloride (2.5 g/L).",
            "chemical": "Foliar spray Carbendazim (1 g/L) or Propiconazole (1 ml/L) at 15-day intervals.",
            "prevention": "Practice crop rotation with non-legumes; practice deep summer plowing to bury crop debris."
        },
        "Healthy": {
            "organic": "Maintain soil organic carbon and beneficial rhizobial nodulation.",
            "chemical": "No treatment required. Crop shows healthy vegetative vigor.",
            "prevention": "Ensure adequate field drainage to prevent waterlogging during flowering."
        },
        "Insect": {
            "organic": "Install yellow sticky traps (15/ha) and spray neem oil 10,000 ppm (2 ml/L) for whiteflies/aphids.",
            "chemical": "Apply Dimethoate 30 EC (1.7 ml/L) or Imidacloprid 17.8 SL (0.3 ml/L).",
            "prevention": "Intercrop with maize or sorghum as border crops to minimize pest vector migration."
        },
        "Leaf Crinkle": {
            "organic": "Rogue out infected stunted plants early to prevent whitefly transmission.",
            "chemical": "Control whitefly vectors using Acetamiprid 20 SP (0.2 g/L).",
            "prevention": "Use certified virus-free seeds and adopt early sowing to evade peak vector populations."
        },
        "Yellow Mosaic": {
            "organic": "Spray NSKE 5% and install yellow sticky traps to reduce Bemisia tabaci (whitefly) vectors.",
            "chemical": "Seed treatment with Imidacloprid 600 FS followed by foliar Thiamethoxam 25 WG.",
            "prevention": "Grow yellow mosaic virus (YMV) resistant varieties; rogue out virus-infected plants immediately."
        }
    },
    "coconut": {
        "Bud Root Dropping": {
            "organic": "Apply 50 kg farmyard manure per palm along with 5 kg neem cake annually.",
            "chemical": "Soil application of balanced NPK + Borax (50 g/palm) and Zinc Sulfate (50 g/palm).",
            "prevention": "Ensure proper irrigation in dry seasons and improve root zone soil aeration."
        },
        "Bud Rot": {
            "organic": "Clean infected bud tissues thoroughly and apply Bordeaux paste (10%) to the crown.",
            "chemical": "Apply Copper Oxychloride (3 g/L) or Metalaxyl-Mancozeb sachet (2 g in palm crown).",
            "prevention": "Provide prophylactic copper fungicidal sprays before monsoon rains commence."
        },
        "Gray Leaf Spot": {
            "organic": "Spray 1% Bordeaux mixture on the lower canopy leaves during initial spotting.",
            "chemical": "Apply Hexaconazole 5 EC (2 ml/L) or Mancozeb (2 g/L) to affected fronds.",
            "prevention": "Cut and burn heavily dried lower fronds; ensure adequate potassium fertilization."
        },
        "Leaf Rot": {
            "organic": "Pour neem oil + garlic emulsion onto the spindle leaves; prune severely affected rotten leaflets.",
            "chemical": "Apply Hexaconazole 5 EC (2 ml) or Mancozeb (3 g) in 300 ml water to the spindle.",
            "prevention": "Treat palms concurrently for rhinoceros beetle damage which creates infection wounds."
        },
        "Stem Bleeding": {
            "organic": "Chisel out infected bleeding bark tissues and coat with coal tar or Bordeaux paste.",
            "chemical": "Apply Calixin (Tridemorph 5 ml in 100 ml water) root feeding or trunk application.",
            "prevention": "Avoid trunk injuries from farm implements; ensure proper drainage around the basin."
        }
    },
    "coffee": {
        "Cerscospora": {
            "organic": "Provide adequate canopy shade; spray 1% Bordeaux mixture during berry development.",
            "chemical": "Spray Copper Oxychloride 50 WP (2.5 g/L) or Chlorothalonil 75 WP (2 g/L).",
            "prevention": "Avoid nutrient starvation in nursery plants; maintain 50-60% filtered shade."
        },
        "Healthy": {
            "organic": "Maintain balanced mulching with coffee cherry pulp and organic manure.",
            "chemical": "No chemicals required. Plant displays normal green foliage.",
            "prevention": "Regular canopy pruning after harvest to maximize interior light balance."
        },
        "Leaf rust": {
            "organic": "Spray 0.5% Bordeaux mixture prior to the monsoon and post-monsoon periods.",
            "chemical": "Apply systemic Triadimefon 25 WP (0.5 g/L) or Hexaconazole 5 EC (1 ml/L).",
            "prevention": "Plant resistant cultivars (e.g. S.795, Cauvery); avoid overly dense bush canopy."
        },
        "Miner": {
            "organic": "Conserve parasitic wasps (Chrysocharis spp.); install pheromone traps.",
            "chemical": "Spray Chlorpyrifos 20 EC or Cartap Hydrochloride 50 SP during peak moth flight.",
            "prevention": "Prune infested suckers; maintain healthy shade to disfavor miner oviposition."
        },
        "Phoma": {
            "organic": "Prune back dieback branches 5 cm below infected tissue and spray copper hydroxide.",
            "chemical": "Spray Pyraclostrobin or Tebuconazole during cold, wet, windy weather.",
            "prevention": "Plant windbreaks along hill ridges to reduce cold wind leaf abrasions."
        }
    },
    "grapes": {
        "Bacterial Leaf Spot": {
            "organic": "Spray copper hydroxide (2 g/L) combined with agricultural streptomycin (100 ppm).",
            "chemical": "Apply Streptocycline (0.5 g/L) combined with Copper Oxychloride (2.5 g/L).",
            "prevention": "Sterilize secateurs during vineyard pruning; remove and burn infected vine canes."
        },
        "Downy Mildew": {
            "organic": "Apply preventative 1% Bordeaux mixture before rain spells; spray potassium phosphonate.",
            "chemical": "Apply Metalaxyl + Mancozeb (2.5 g/L) or Dimethomorph (1 g/L) to leaf undersides.",
            "prevention": "Shoot thinning to improve airflow; avoid micro-sprinklers that wet grape foliage."
        },
        "Healthy Leaves": {
            "organic": "Maintain regular foliar seaweed extract and canopy aeration.",
            "chemical": "No chemical application needed. Vines are healthy.",
            "prevention": "Regular canopy management, balanced nitrogen/calcium ratio, and drip irrigation."
        },
        "Powdery Mildew": {
            "organic": "Apply wettable sulfur (2 g/L) or potassium bicarbonate (4 g/L) on leaf surfaces.",
            "chemical": "Foliar spray of Difenoconazole 25 EC (0.5 ml/L) or Penconazole 10 EC (0.5 ml/L).",
            "prevention": "Ensure good sun penetration through the vine trellis; avoid excessive nitrogen."
        }
    },
    "jute": {
        "Cescospora Leaf Spot": {
            "organic": "Spray neem oil 1% or copper oxychloride (2 g/L) at first symptom appearance.",
            "chemical": "Apply Carbendazim 50 WP (1 g/L) or Mancozeb 75 WP (2.5 g/L).",
            "prevention": "Treat seeds with Trichoderma viride (10 g/kg) before sowing; practice crop rotation."
        },
        "Golden Mosaic": {
            "organic": "Spray neem seed kernel extract (NSKE 5%) to repel whitefly insect vectors.",
            "chemical": "Foliar spray Acetamiprid 20 SP (0.25 g/L) or Thiamethoxam 25 WG (0.3 g/L).",
            "prevention": "Use clean disease-free certified seeds; rogue out virus-infected jute plants early."
        },
        "Healthy Leaf": {
            "organic": "Maintain optimal organic compost dressing and soil moisture.",
            "chemical": "No chemicals needed. Jute fiber plants are vigorous and healthy.",
            "prevention": "Keep field free of weed hosts and ensure adequate soil nitrogen levels."
        }
    },
    "maize": {
        "Blight": {
            "organic": "Foliar spray of Trichoderma harzianum bio-agent; prune heavily blighted lower leaves.",
            "chemical": "Apply Mancozeb 75 WP (2.5 g/L) or Azoxystrobin (1 ml/L) at knee-high stage.",
            "prevention": "Rotate maize with soybean or cowpea; destroy leftover maize stalk stubble."
        },
        "Common_Rust": {
            "organic": "Apply sulfur dust (25 kg/ha) or Bacillus amyloliquefaciens bio-fungicide.",
            "chemical": "Apply Pyraclostrobin or Propiconazole 25 EC (1 ml/L) upon pustule formation.",
            "prevention": "Plant rust-tolerant hybrid seeds; sow early in the season to evade late-season spore peaks."
        },
        "Gray_Leaf_Spot": {
            "organic": "Incorporate crop residues deeply; apply copper-based organic protectorants.",
            "chemical": "Spray Azoxystrobin + Difenoconazole combination fungicide (1 ml/L).",
            "prevention": "Practice 2-year crop rotation; avoid continuous no-till monoculture corn fields."
        },
        "Healthy": {
            "organic": "Maintain optimal compost application and regular root-zone soil moisture.",
            "chemical": "No chemical intervention needed. Corn crop is flourishing.",
            "prevention": "Monitor for armyworm pests and maintain balanced nitrogen/zinc nutrition."
        }
    },
    "mango": {
        "Alternaria": {
            "organic": "Spray copper oxychloride (2.5 g/L) or neem-based bio-formulation.",
            "chemical": "Foliar spray Mancozeb (2.5 g/L) or Iprodione (2 g/L) during flush emergence.",
            "prevention": "Prune criss-cross branches to reduce orchard humidity and improve sunlight."
        },
        "Anthracnose": {
            "organic": "Apply 1% Bordeaux mixture before panicle flowering; post-harvest hot water fruit dip (52°C for 5 min).",
            "chemical": "Spray Carbendazim 50 WP (1 g/L) or Azoxystrobin 23 SC (1 ml/L) during blossom.",
            "prevention": "Prune out dead terminal twigs; spray copper fungicides after post-harvest pruning."
        },
        "Black Mould Rot": {
            "organic": "Control scale insects and mealybugs whose honeydew secretions foster sooty mold.",
            "chemical": "Spray starch solution (20 g/L) which flakes off mould upon drying; spray systemic insecticide.",
            "prevention": "Wash trees with mild detergent solution; control sucking insects promptly."
        },
        "Healthy": {
            "organic": "Maintain balanced compost, paclobutrazol (if applied by agronomist), and micronutrients.",
            "chemical": "No chemical treatment needed. Tree canopy exhibits healthy vigor.",
            "prevention": "Regular orchard hygiene, balanced drip irrigation, and post-harvest sanitation."
        },
        "Stem and Rot": {
            "organic": "Paste cut stem ends with cow dung + copper oxychloride mixture after harvesting.",
            "chemical": "Apply Carbendazim (1 g/L) or Thiophanate Methyl (1.5 g/L) trunk drench.",
            "prevention": "Harvest mangoes with 1-2 cm pedicel attached; avoid dropping fruit onto hard soil."
        },
        "Stem end Rot": {
            "organic": "Dip harvested fruits in hot water (52°C) for 5 minutes; avoid mechanical stem bruising.",
            "chemical": "Pre-harvest spray of Prochloraz (1 ml/L) or Azoxystrobin 15 days before harvest.",
            "prevention": "Keep harvesting crates sanitized; avoid packing fruit under rainy conditions."
        }
    },
    "orange": {
        "blackspot": {
            "organic": "Apply copper hydroxide (2 g/L) at 2/3 petal fall and repeat 4-6 weeks later.",
            "chemical": "Foliar spray Pyraclostrobin or Kresoxim-methyl according to citrus spray schedule.",
            "prevention": "Mulch fallen orchard leaves with organic matter to speed up decomposition of spores."
        },
        "canker": {
            "organic": "Prune cankered shoots during winter and spray 1% Bordeaux mixture or copper bactericide.",
            "chemical": "Spray Streptocycline (100 ppm) combined with Copper Oxychloride (2.5 g/L).",
            "prevention": "Install windbreaks around citrus orchard; control citrus leafminer to stop wound sites."
        },
        "fresh": {
            "organic": "Maintain balanced zinc, iron, and manganese micronutrient foliar sprays.",
            "chemical": "No chemicals required. Citrus foliage is fresh and healthy.",
            "prevention": "Continue regular pest scouting for aphids, psyllids, and spider mites."
        },
        "grenning": {
            "organic": "Inject or spray micronutrient cocktails (Zn, Fe, Mn) to support tree vigor; install yellow traps.",
            "chemical": "Control Asian Citrus Psyllid (Diaphorina citri) vectors using Imidacloprid or Dimethoate.",
            "prevention": "Plant only certified disease-free grafted saplings; rogue out severely infected trees."
        }
    },
    "pigonpea": {
        "Healthy": {
            "organic": "Maintain balanced soil fertility and conserve native predatory wasps.",
            "chemical": "No chemicals required. Pigeon pea crop is vigorous and healthy.",
            "prevention": "Ensure ridge planting for rapid drainage during heavy monsoon showers."
        },
        "Leaf_Spot": {
            "organic": "Spray neem seed kernel extract (NSKE 5%) or copper oxychloride (2.5 g/L).",
            "chemical": "Apply Mancozeb 75 WP (2 g/L) or Carbendazim (1 g/L) at initial spot detection.",
            "prevention": "Destroy previous crop residues; rotate pigeon pea with sorghum, pearl millet, or maize."
        },
        "Leaf_webber": {
            "organic": "Handpick and destroy webbed leaf clusters; spray Bacillus thuringiensis (Bt) @ 1.5 g/L.",
            "chemical": "Foliar spray Chlorantraniliprole 18.5 SC (0.3 ml/L) or Indoxacarb 14.5 SC (0.5 ml/L).",
            "prevention": "Conserve predatory spider populations; install light traps to capture adult moths."
        },
        "Sterilic_mosaic": {
            "organic": "Rogue out infected chlorotic bushes early; spray wettable sulfur (3 g/L) to suppress mites.",
            "chemical": "Spray Propargite 57 EC (2 ml/L) or Fenpyroximate 5 EC (1 ml/L) to control Aceria eriophyid mites.",
            "prevention": "Sow sterility mosaic resistant cultivars (e.g. BSMR 736, Asha); avoid ratooning."
        }
    },
    "rice": {
        "BrownSpot": {
            "organic": "Seed treatment with Pseudomonas fluorescens (10 g/kg seed); apply balanced silicon and potassium.",
            "chemical": "Spray Propiconazole 25 EC (1 ml/L) or Mancozeb 75 WP (2 g/L) at boot-leaf stage.",
            "prevention": "Correct soil potassium and silicon deficiencies; avoid prolonged drought stress."
        },
        "Healthy": {
            "organic": "Maintain optimal Azolla biofertilizer and alternate wetting and drying (AWD) water management.",
            "chemical": "No chemicals required. Rice foliage is healthy and emerald green.",
            "prevention": "Scout weekly for stem borers, leaf folders, and plant hoppers."
        },
        "Hispa": {
            "organic": "Sweep nets to trap adult hispa beetles; clip and burn leaf tips before transplanting.",
            "chemical": "Spray Chlorpyrifos 20 EC (2 ml/L) or Quinalphos 25 EC (2 ml/L) when leaf damage exceeds 10%.",
            "prevention": "Avoid excessive nitrogen application which promotes succulent hispa-attracting foliage."
        },
        "LeafBlast": {
            "organic": "Seed treatment and foliar spray with Pseudomonas fluorescens (5 g/L).",
            "chemical": "Apply Tricyclazole 75 WP (0.6 g/L) or Isoprothiolane 40 EC (1.5 ml/L).",
            "prevention": "Avoid split heavy urea applications; maintain water layer in paddy during blast-prone weather."
        }
    },
    "watermelon": {
        "Anthracnose": {
            "organic": "Apply preventative bio-fungicide Bacillus subtilis or copper hydroxide (2 g/L).",
            "chemical": "Apply Chlorothalonil 75 WP (2 g/L) or Azoxystrobin (1 ml/L) at 7-10 day intervals.",
            "prevention": "Use certified anthracnose-free seed; avoid overhead irrigation that keeps vines wet."
        },
        "Downy_Mildew": {
            "organic": "Spray potassium phosphonate (2 ml/L) or dilute neem oil emulsion on leaf undersides.",
            "chemical": "Apply Cymoxanil + Mancozeb (2 g/L) or Dimethomorph (1 g/L) during humid cloudy spells.",
            "prevention": "Provide wide plant spacing and drip irrigation; plant downy mildew-tolerant hybrids."
        },
        "Healthy": {
            "organic": "Maintain organic straw mulch and balanced drip fertigation.",
            "chemical": "No chemicals needed. Watermelon foliage and vines are healthy.",
            "prevention": "Regular inspection under leaves for red spider mites and aphids."
        },
        "Mosaic_Virus": {
            "organic": "Rogue out infected mosaic-patterned vines immediately; use reflective silver mulches to repel vectors.",
            "chemical": "Spray Acetamiprid 20 SP (0.2 g/L) or Imidacloprid (0.3 ml/L) to control aphid vectors.",
            "prevention": "Eradicate cucurbit weeds around field borders; disinfect pruning tools between plants."
        }
    }
}

# Generic fallback advisory for ambiguous or unspecified plant species
GENERIC_ADVISORY: Dict[str, Dict[str, str]] = {
    "fungal": {
        "organic": "Prune visibly affected leaves; apply copper-based fungicide or neem oil (0.5%) in morning hours.",
        "chemical": "Apply broad-spectrum systemic fungicide (e.g., Mancozeb or Azoxystrobin) following label guidelines.",
        "prevention": "Water only at the root base; space plants for airflow and sanitize cutting tools."
    },
    "viral": {
        "organic": "Remove and dispose of severely mottled leaves; install insect traps to reduce vector populations.",
        "chemical": "Viruses cannot be cured chemically. Control insect vectors (aphids/whiteflies) using targeted insecticides.",
        "prevention": "Use certified clean seed stock; remove wild weed reservoirs near cultivation beds."
    },
    "bacterial": {
        "organic": "Prune infected stems 10 cm below lesion; spray copper hydroxide or potassium bicarbonate.",
        "chemical": "Apply agricultural bactericide (e.g. Copper Oxychloride + Streptocycline) under agronomist guidance.",
        "prevention": "Never work in wet fields; sterilize shears in 70% alcohol between cuts."
    },
    "healthy": {
        "organic": "Continue balanced organic soil amendment and compost tea application.",
        "chemical": "No treatment required. Plant tissues display normal physiological vigor.",
        "prevention": "Maintain regular watering schedule and scout weekly for early pathogen symptoms."
    },
    "uncertain": {
        "organic": "Take a new close-up photo in bright, indirect natural sunlight. Capture the entire leaf with sharp focus.",
        "chemical": "Do not apply chemical sprays until the disease is conclusively diagnosed.",
        "prevention": "Inspect both top and underside of the leaf; isolate suspect plants if symptoms rapidly progress."
    }
}


def get_treatment_advisory(crop_key: str, disease_name: str, is_healthy: bool, is_uncertain: bool) -> Dict[str, str]:
    """
    Retrieve curated organic, chemical, and preventative treatment advice
    for a given plant and diagnosed condition.

    Inputs:
        crop_key: str - Normalized crop key, e.g. 'apple'
        disease_name: str - Diagnosed disease class name
        is_healthy: bool - Flag whether leaf is healthy
        is_uncertain: bool - Flag whether model confidence was below threshold

    Outputs:
        Dict[str, str] with keys: 'organic', 'chemical', 'prevention'
    """
    if is_uncertain:
        return GENERIC_ADVISORY["uncertain"]

    # Check crop-specific knowledge base
    crop_dict = TREATMENT_ADVISORY.get(crop_key.lower().strip())
    if crop_dict:
        # Exact match
        if disease_name in crop_dict:
            return crop_dict[disease_name]
        # Case-insensitive / partial match
        d_lower = disease_name.lower()
        for key, adv in crop_dict.items():
            if key.lower() == d_lower or key.lower() in d_lower or d_lower in key.lower():
                return adv

    # Fallback heuristic based on pathology keywords
    d_lower = disease_name.lower()
    if is_healthy or "healthy" in d_lower or "fresh" in d_lower:
        return GENERIC_ADVISORY["healthy"]
    if any(k in d_lower for k in ["mosaic", "virus", "crinkle"]):
        return GENERIC_ADVISORY["viral"]
    if any(k in d_lower for k in ["bacterial", "canker"]):
        return GENERIC_ADVISORY["bacterial"]

    # Default to fungal (vast majority of foliar spots/rusts/mildews/rots)
    return GENERIC_ADVISORY["fungal"]


# ---------------------------------------------------------------------------
# Supported Crops Helper
# ---------------------------------------------------------------------------
def get_supported_crops() -> List[Dict[str, str]]:
    """
    Return list of all 13 supported crops with keys and user-friendly display names.

    Outputs:
        List of dicts: [{"key": "apple", "name": "Apple"}, ...]
    """
    return [{"key": k, "name": v["name"]} for k, v in DATASET_CONFIG.items()]


# ---------------------------------------------------------------------------
# Model Cleanup & Download Helpers
# ---------------------------------------------------------------------------
def cleanup_old_models(keep_filename: Optional[str] = None) -> None:
    """
    Remove previously cached .keras files on disk except the active one.
    Crucial on Render ephemeral disks to stay within disk quotas.

    Inputs:
        keep_filename: str | None - The filename currently needed by the active prediction.
    """
    try:
        if os.path.exists(MODEL_DIR):
            for fname in os.listdir(MODEL_DIR):
                if fname.endswith(".keras") and fname != keep_filename:
                    fpath = os.path.join(MODEL_DIR, fname)
                    try:
                        os.remove(fpath)
                        logger.info(f"Evicted cached model file from disk: {fname}")
                    except Exception as e:
                        logger.warning(f"Could not remove {fname}: {e}")
    except Exception as e:
        logger.warning(f"Cleanup warning: {e}")


def download_model_if_missing(model_filename: str, target_path: str) -> str:
    """
    Ensure the .keras model file is present on disk. If missing (e.g. fresh Render container),
    downloads it from Hugging Face Hub or direct CDN URL.

    Inputs:
        model_filename: str - e.g. 'apple_resnet50_finetuned.keras'
        target_path: str - Absolute destination path on disk

    Outputs:
        str - Verified path to the downloaded model file

    Raises:
        FileNotFoundError if the model cannot be obtained from any source.
    """
    # If file exists and is reasonably large (> 10MB), return immediately
    if os.path.isfile(target_path) and os.path.getsize(target_path) > 10 * 1024 * 1024:
        return target_path

    # Clean disk space of other crop models before downloading new ~210MB file
    cleanup_old_models(keep_filename=model_filename)

    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    hf_repo = HF_REPO_ID or DEFAULT_HF_REPO
    download_errors: List[str] = []

    # 1. Option A: Download via huggingface_hub Python library
    try:
        from huggingface_hub import hf_hub_download
        logger.info(f"Downloading {model_filename} from Hugging Face repository '{hf_repo}'...")
        downloaded = hf_hub_download(
            repo_id=hf_repo,
            filename=f"disease/{model_filename}",
            local_dir=os.path.dirname(os.path.dirname(target_path))  # models/
        )
        if os.path.isfile(downloaded) and os.path.getsize(downloaded) > 10 * 1024 * 1024:
            logger.info(f"HF Hub download complete: {downloaded}")
            return downloaded
    except Exception as e:
        logger.warning(f"HF Hub library download failed: {e}")
        download_errors.append(f"HF Hub: {e}")

    # 2. Option B: Direct HTTP streaming with resume and chunking
    candidate_urls = [
        f"https://huggingface.co/{hf_repo}/resolve/main/disease/{model_filename}"
    ]
    raw_base = os.getenv("MODEL_BASE_URL")
    if raw_base and raw_base.strip():
        candidate_urls.insert(0, f"{raw_base.strip().rstrip('/')}/{model_filename}")

    for url in candidate_urls:
        tmp_path = f"{target_path}.tmp"
        try:
            logger.info(f"Streaming {model_filename} directly from {url}...")
            req = urllib.request.Request(url, headers={"User-Agent": "SmartAgricultureAssistant/1.0"})
            with urllib.request.urlopen(req, timeout=180) as response, open(tmp_path, "wb") as out_file:
                chunk_size = 1024 * 1024  # 1MB buffer
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)

            if os.path.isfile(tmp_path) and os.path.getsize(tmp_path) > 10 * 1024 * 1024:
                os.replace(tmp_path, target_path)
                size_mb = os.path.getsize(target_path) / (1024 * 1024)
                logger.info(f"Successfully saved {model_filename} ({size_mb:.1f} MB)")
                return target_path
            else:
                if os.path.isfile(tmp_path):
                    os.remove(tmp_path)
                raise ValueError("Downloaded file is smaller than 10MB or corrupted.")
        except Exception as e:
            if os.path.isfile(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            logger.warning(f"Direct stream download failed from {url}: {e}")
            download_errors.append(f"{url}: {e}")

    err_summary = "; ".join(download_errors)
    raise FileNotFoundError(
        f"Unable to download model '{model_filename}' to {target_path}. Errors: {err_summary}"
    )


# ---------------------------------------------------------------------------
# Model Loader with Thread-Safe Cache
# ---------------------------------------------------------------------------
def load_crop_disease_model(crop_key: str) -> Tuple[Any, Any]:
    """
    Thread-safe lazy-load for the requested crop model and its label encoder.
    Evicts previously loaded crop models from RAM to stay strictly within
    Render's 512 MB memory boundary.

    Inputs:
        crop_key: str - Normalized crop key, e.g. 'apple', 'rice'

    Outputs:
        Tuple[keras.Model, LabelEncoder]

    Raises:
        ValueError if crop_key is unsupported.
        FileNotFoundError if model weights or encoder cannot be found.
    """
    global _current_crop, _current_model, _current_encoder, _is_warming_up

    crop_key = crop_key.lower().strip()
    if crop_key not in DATASET_CONFIG:
        raise ValueError(f"Unsupported crop '{crop_key}'. Supported crops: {list(DATASET_CONFIG.keys())}")

    # Fast path: Return cached model if already loaded in this process
    if _current_crop == crop_key and _current_model is not None:
        return _current_model, _current_encoder

    # Acquire lock so concurrent HTTP requests do not duplicate model loading or downloads
    with _model_lock:
        # Re-check inside critical section
        if _current_crop == crop_key and _current_model is not None:
            return _current_model, _current_encoder

        _is_warming_up = True
        try:
            # 1. Import TensorFlow lazily inside the loader so the web server starts instantly
            import tensorflow as tf
            from tensorflow import keras
            from tensorflow.keras.applications.resnet50 import preprocess_input

            # 2. Free RAM from previous model before loading new one
            if _current_model is not None:
                logger.info(f"Evicting previous model for crop '{_current_crop}' from RAM...")
                del _current_model
                del _current_encoder
                _current_model = None
                _current_encoder = None
                keras.backend.clear_session()
                gc.collect()

            config = DATASET_CONFIG[crop_key]
            model_path = os.path.join(MODEL_DIR, config["model"])
            encoder_path = os.path.join(ENCODER_DIR, config["encoder"])

            # 3. Ensure model file is present on disk (downloads on demand if needed)
            model_path = download_model_if_missing(config["model"], model_path)

            if not os.path.isfile(encoder_path):
                raise FileNotFoundError(f"Label encoder file missing: {encoder_path}")

            # 4. Load trained Keras model with ResNet50 preprocessing custom object
            logger.info(f"Loading Keras model into memory: {config['model']}...")
            loaded_model = keras.models.load_model(
                model_path,
                compile=False,
                safe_mode=False,
                custom_objects={"preprocess_input": preprocess_input}
            )

            # 5. Load dataset-specific Scikit-Learn LabelEncoder
            with open(encoder_path, "rb") as f:
                loaded_encoder = pickle.load(f)

            _current_model = loaded_model
            _current_encoder = loaded_encoder
            _current_crop = crop_key
            logger.info(f"Model for crop '{crop_key}' successfully loaded into memory.")

            return _current_model, _current_encoder
        finally:
            _is_warming_up = False


# ---------------------------------------------------------------------------
# Preprocessing Pipeline Matching Training
# ---------------------------------------------------------------------------
def preprocess_leaf_image(image_bytes: bytes) -> np.ndarray:
    """
    Preprocess raw uploaded image bytes to exactly match the training pipeline.

    Preprocessing steps:
    1. Decode image via PIL.
    2. Verify file integrity to catch corrupted uploads.
    3. Convert to 3-channel RGB.
    4. Resize to target dimension (224, 224).
    5. Convert to float32 NumPy array.
    6. NORMALIZE PIXELS TO [0.0, 1.0] by dividing by 255.0.
       (Why: The model contains internal `layers.Rescaling(scale=255.0)` and
        `preprocess_input` layers. Supplying [0, 1] allows the internal layer to
        scale to [0, 255] as designed, avoiding activation explosion).
    7. Expand batch dimension to (1, 224, 224, 3).

    Inputs:
        image_bytes: bytes - Raw uploaded image file bytes

    Outputs:
        np.ndarray - Preprocessed tensor of shape (1, 224, 224, 3) and dtype float32

    Raises:
        ValueError if the image cannot be decoded or is corrupted.
    """
    # Pillow is only needed for image prediction. Keep it lazy so lightweight
    # health and supported-crops endpoints can start without the image stack.
    from PIL import Image

    if not image_bytes or len(image_bytes) == 0:
        raise ValueError("Uploaded image file is empty (0 bytes).")

    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        size_mb = len(image_bytes) / (1024 * 1024)
        max_mb = MAX_IMAGE_SIZE_BYTES / (1024 * 1024)
        raise ValueError(f"Image size ({size_mb:.1f} MB) exceeds maximum allowed limit ({max_mb:.0f} MB).")

    try:
        # Decode and verify integrity
        raw_stream = BytesIO(image_bytes)
        pil_img = Image.open(raw_stream)
        pil_img.verify()

        # Reopen image after verify() (PIL closes stream after verify)
        raw_stream.seek(0)
        pil_img = Image.open(raw_stream)
    except Exception as decode_err:
        logger.error(f"Image decode failed: {decode_err}")
        raise ValueError("Invalid or corrupted image file. Please upload a valid JPG, PNG, or WEBP photo.")

    # 1. Ensure 3-channel RGB (converts RGBA, Grayscale, CMYK)
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")

    # 2. Resize to 224 x 224 with high-quality resampling
    pil_img = pil_img.resize(IMAGE_SIZE, Image.Resampling.BILINEAR)

    # 3. Convert to float32 NumPy array
    img_array = np.asarray(pil_img, dtype=np.float32)

    # 4. NORMALIZATION: Divide by 255.0 to scale to [0.0, 1.0].
    # Crucial: The model contains `layers.Rescaling(scale=255.0)` before ResNet50 preprocessing.
    img_array = img_array / 255.0

    # 5. Add batch dimension: (1, 224, 224, 3)
    img_batch = np.expand_dims(img_array, axis=0)

    return img_batch


# ---------------------------------------------------------------------------
# Prediction Service
# ---------------------------------------------------------------------------
def predict_disease(image_bytes: bytes, crop_key: str) -> Dict[str, Any]:
    """
    Diagnose foliar plant disease from leaf image bytes and selected crop.

    Features:
    - Preprocesses input exactly to [0.0, 1.0] range.
    - Evaluates against confidence threshold (default 0.60).
    - Returns top-3 predictions with confidence percentages.
    - Attaches comprehensive treatment (organic & chemical) and prevention advice.

    Inputs:
        image_bytes: bytes - Uploaded image binary data
        crop_key: str - Target crop species key (e.g. 'apple')

    Outputs:
        Dict[str, Any] containing:
            - plant: Display name of the plant
            - crop_key: Key of the crop
            - disease: Top predicted disease name (or 'Uncertain...' if below threshold)
            - confidence: Confidence percentage (0-100)
            - is_healthy: Boolean flag
            - is_uncertain: Boolean flag indicating if confidence < threshold
            - status_message: User-friendly status message
            - top_predictions: List of top 3 candidate predictions
            - treatment: Dict with organic, chemical, and prevention advice

    Raises:
        ValueError for input or format errors.
        FileNotFoundError if model weights cannot be downloaded/loaded.
    """
    crop_key = crop_key.lower().strip()
    if crop_key not in DATASET_CONFIG:
        raise ValueError(f"Unsupported crop '{crop_key}'. Supported crops: {list(DATASET_CONFIG.keys())}")

    # 1. Preprocess leaf image (raises ValueError on bad image)
    img_batch = preprocess_leaf_image(image_bytes)

    # 2. Lazy load model and encoder for this crop
    model, encoder = load_crop_disease_model(crop_key)

    # 3. Run neural network inference
    raw_probs = model.predict(img_batch, verbose=0)[0]

    # 4. Extract Top-3 predictions
    classes_list = encoder.classes_
    num_classes = len(classes_list)
    top_k = min(3, num_classes)
    top_indices = np.argsort(raw_probs)[::-1][:top_k]

    top_predictions: List[Dict[str, Any]] = []
    for idx in top_indices:
        class_name = str(classes_list[idx])
        conf_pct = round(float(raw_probs[idx]) * 100.0, 2)
        top_predictions.append({
            "disease": class_name,
            "confidence": conf_pct
        })

    # Top-1 result details
    best_class = top_predictions[0]["disease"]
    best_conf = top_predictions[0]["confidence"]
    best_conf_fraction = float(raw_probs[top_indices[0]])

    # 5. Check confidence threshold
    is_uncertain = best_conf_fraction < CONFIDENCE_THRESHOLD

    if is_uncertain:
        disease_display = "Uncertain - please upload a clearer leaf image"
        status_message = (
            f"Prediction confidence ({best_conf:.1f}%) is below the {CONFIDENCE_THRESHOLD * 100:.0f}% certainty threshold. "
            f"Please take a clearer, well-lit photo focusing on the affected leaf surface."
        )
        is_healthy = False
    else:
        disease_display = best_class
        is_healthy = "healthy" in best_class.lower() or "fresh" in best_class.lower()
        if is_healthy:
            status_message = "Leaf appears healthy with no conspicuous symptoms of pathogenic infection."
        else:
            status_message = f"Pathology detected: {best_class} ({best_conf:.1f}% confidence)."

    # 6. Retrieve treatment and prevention advisory
    treatment = get_treatment_advisory(
        crop_key=crop_key,
        disease_name=best_class,
        is_healthy=is_healthy,
        is_uncertain=is_uncertain
    )

    plant_display_name = DATASET_CONFIG[crop_key]["name"]

    return {
        "plant": plant_display_name,
        "crop_key": crop_key,
        "disease": disease_display,
        "raw_disease": best_class,
        "confidence": best_conf,
        "is_healthy": is_healthy,
        "is_uncertain": is_uncertain,
        "status_message": status_message,
        "threshold": round(CONFIDENCE_THRESHOLD * 100.0, 1),
        "top_predictions": top_predictions,
        "treatment": treatment
    }


# ---------------------------------------------------------------------------
# Module Health Check Helper
# ---------------------------------------------------------------------------
def get_disease_health() -> Dict[str, Any]:
    """
    Report the operational status of the disease detection module.
    Useful for uptime monitors and readiness checks.
    """
    return {
        "status": "ok",
        "supported_crops_count": len(DATASET_CONFIG),
        "active_cached_crop": _current_crop,
        "model_loaded": _current_model is not None,
        "is_warming_up": _is_warming_up,
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "hf_repository": HF_REPO_ID or DEFAULT_HF_REPO,
        "model_directory_exists": os.path.exists(MODEL_DIR),
        "encoder_directory_exists": os.path.exists(ENCODER_DIR)
    }
