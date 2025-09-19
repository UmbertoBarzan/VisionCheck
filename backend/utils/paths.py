import os
from pathlib import Path

# Percorso assoluto alla radice del progetto
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Percorsi interni
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = ROOT_DIR / "backend" / "models"
CONFIGS_DIR = ROOT_DIR / "configs"
DATASETS_DIR = ROOT_DIR / "datasets"


# Crea le cartelle se non esistono (es. data/)
for directory in [DATA_DIR, MODELS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
