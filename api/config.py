from pathlib import Path

BASE_DIR = Path(__file__).parent

DB_PATH = BASE_DIR / "wildlife.db"

IMAGES_DIR = BASE_DIR / "images"

MODELS_DIR = BASE_DIR / "../src/checkpoints\\run_20260827T054817Z"

IMAGES_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
