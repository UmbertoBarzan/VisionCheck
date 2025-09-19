from pathlib import Path
import uuid
import yaml

from utils.paths import MODELS_DIR, DATA_DIR, CONFIGS_DIR, DATASETS_DIR
from utils.logger import get_logger

from anomalib.data import Folder
from anomalib.engine import Engine
from anomalib.models import (
    Padim, Patchcore, ReverseDistillation, Cfa, Cflow, 
    EfficientAd, Stfpm, Draem, Dsr, Fastflow, Uflow
)

from PIL import Image
import cv2
import numpy as np

import torch
from torchvision import transforms
from PIL import Image

from matplotlib import cm
from matplotlib.colors import Normalize, LinearSegmentedColormap

logger = get_logger('anomalib')

def load_anomalib_models_config(yaml_path: Path) -> list[dict]:
    '''Carica i modelli Anomalib attivi da un file di configurazione YAML.'''
    if not yaml_path.exists():
        logger.error(f"File YAML non trovato: {yaml_path}")
        return []

    with open(yaml_path, "r") as f:
        config = yaml.safe_load(f)

    enabled = [entry for entry in config if not entry.get("disabled", False)]
    logger.info(f"Modelli Anomalib attivi: {[m['name'] for m in enabled]}")
    print(f'Enabled models: {enabled}')
    return enabled

def load_anomalib_model(model_entry: dict):
    '''Crea un'istanza del modello Anomalib specificato nell'entry del dizionario.'''
    model_name = model_entry["model"]
    model_class = {
        "Padim": Padim,
        "Patchcore": Patchcore,
        "Draem": Draem,
        "Cfa": Cfa,
        "ReverseDistillation": ReverseDistillation,
        "EfficientAd": EfficientAd,
    }.get(model_name)

    if not model_class:
        logger.error(f"Classe modello non trovata per: {model_name}")
        return None
    
    params = model_entry.get("model_params", {}) or {}
    
    model = model_class(**params)
    logger.info(f"Modello '{model_name}' istanziato con parametri: {params}")
    return model

def prepare_folder_datamodule(dataset_name: str) -> Folder:
    '''Prepara un datamodule per il dataset specificato.'''
    datamodule = Folder(
        name=dataset_name,
        root=DATASETS_DIR / dataset_name,
        normal_dir='good',
        abnormal_dir='crack',
        mask_dir=DATASETS_DIR / dataset_name / "mask" / "crack"
    )

    datamodule.setup()
    
    logger.info(f"Dataset '{dataset_name}' pronto con {len(datamodule.train_data)} train e {len(datamodule.test_data)} test.")
    return datamodule

def train_enabled_models():
    '''Addestra tutti i modelli Anomalib abilitati.'''
    models = load_anomalib_models_config(CONFIGS_DIR / "anomalib_models.yaml")
    if not models:
        logger.error("Nessun modello abilitato trovato.")
        return

    datamodule = prepare_folder_datamodule("hazelnut_toy")  # TODO: non hardcodare

    for model_entry in models:
        model = load_anomalib_model(model_entry)
        if model is None:
            logger.warning(f"⚠️ Modello '{model_entry['name']}' non caricato, salto.")
            continue

        logger.info(f"🚀 Inizio training: {model_entry['name']}")

        engine = Engine()
        engine.fit(model=model, datamodule=datamodule)

        logger.info(f"✅ Training completato: {model_entry['name']}")
    
def get_latest_ckpt_path(model_name: str, dataset_name: str) -> Path | None:
    model_dir = Path('results') / model_name / dataset_name
    latest = model_dir / 'latest' / 'weights' / 'lightning'
    ckpt = latest / 'model.ckpt'
    
    if ckpt.exists():
        logger.info(f"Ultimo checkpoint trovato: {ckpt}")
        return ckpt
    else:
        logger.error(f"Nessun checkpoint trovato in: {ckpt}")
        return None


def load_checkpoint_with_fallback(model_class, ckpt_path: Path, model_entry: dict):
    '''Carica un modello Anomalib gestendo checkpoint legacy senza campo transform.'''
    if ckpt_path is None:
        return None

    map_location = torch.device("cpu")
    try:
        model = model_class.load_from_checkpoint(
            checkpoint_path=str(ckpt_path),
            map_location=map_location,
        )
        logger.info(f"✅ Checkpoint loaded for {model_entry['name']} ({model_entry['model']})")
        return model
    except KeyError as exc:
        if 'transform' not in str(exc):
            raise

        logger.warning(
            "⚠️ Checkpoint for %s is missing 'transform'. Falling back to manual state_dict load.",
            model_entry['name'],
        )

    checkpoint = torch.load(str(ckpt_path), map_location=map_location)
    state_dict = checkpoint.get("state_dict")
    if state_dict is None:
        logger.error(f"❌ state_dict missing from checkpoint {ckpt_path}")
        return None

    params = model_entry.get("model_params", {}) or {}
    model = model_class(**params)
    incompatible = model.load_state_dict(state_dict, strict=False)

    if getattr(incompatible, "missing_keys", None):
        logger.warning(
            "⚠️ Missing keys while loading %s: %s",
            model_entry['name'],
            incompatible.missing_keys,
        )
    if getattr(incompatible, "unexpected_keys", None):
        logger.warning(
            "⚠️ Unexpected keys while loading %s: %s",
            model_entry['name'],
            incompatible.unexpected_keys,
        )

    logger.info(f"✅ State_dict loaded for {model_entry['name']}")
    return model

def color_anomaly_map(anomaly_map: np.ndarray, image: np.ndarray | None = None) -> np.ndarray:
    """Colora l'anomaly map con una colormap personalizzata (viola → magenta → arancione) + contorni arancioni."""

    # Normalizzazione della anomaly map
    norm_map = cv2.normalize(anomaly_map, None, 0, 1.0, cv2.NORM_MINMAX)

    # Colormap personalizzata (viola → magenta → arancio)
    colors = [
        (0.0, (0.45, 0.0, 0.5)),    # viola
        (0.3, (0.8, 0.2, 0.6)),     # magenta
        (0.6, (1.0, 0.7, 0.3)),     # arancio chiaro
        (1.0, (1.0, 0.4, 0.0)),     # arancio intenso
    ]
    cmap = LinearSegmentedColormap.from_list("patchcore", colors)
    colored = (cmap(norm_map)[..., :3] * 255).astype(np.uint8)

    # Se l'immagine di input è disponibile, facciamo l'overlay
    if image is not None:
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        overlay = cv2.addWeighted(image_rgb, 0.6, colored, 0.4, 0)  # maggiore saturazione per un overlay più visibile
    else:
        overlay = colored

    # Soglia dinamica (usiamo il 90° percentile per le anomalie più significative)
    threshold = np.percentile(anomaly_map, 90)
    _, binary_mask = cv2.threshold(anomaly_map, threshold, 255, cv2.THRESH_BINARY)

    # Trova contorni per le anomalie
    contours, _ = cv2.findContours(binary_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Disegna contorni arancioni spessi
    thickness = max(2, int(image.shape[0] / 100))  # Aumento della larghezza dei contorni
    for contour in contours:
        cv2.drawContours(overlay, [contour], -1, (255, 100, 0), thickness)  # Colore arancione (255, 100, 0)

    # Restituisce l'overlay finale
    return overlay
    
def run_anomalib(image_path: Path) -> Path | None:
    models = load_anomalib_models_config(CONFIGS_DIR / "anomalib_models.yaml")
    if not models:
        logger.error("Nessun modello attivo trovato.")
        return None

    image_cv = cv2.imread(str(image_path))
    image_rgb = cv2.cvtColor(image_cv, cv2.COLOR_BGR2RGB)
    image_pil = Image.fromarray(image_rgb)

    output_path = DATA_DIR / "anomalib"
    output_path.mkdir(parents=True, exist_ok=True)

    paths = []

    for model_entry in models:
        model_name = model_entry["model"]

        if model_name == "Padim":
            ckpt_path = get_latest_ckpt_path("Padim", "hazelnut_toy")
            model = load_checkpoint_with_fallback(Padim, ckpt_path, model_entry)
        elif model_name == "Patchcore":
            ckpt_path = get_latest_ckpt_path("Patchcore", "hazelnut_toy")
            model = load_checkpoint_with_fallback(Patchcore, ckpt_path, model_entry)
        else:
            logger.warning(f"🔕 Modello {model_name} non supportato in run_anomalib per ora.")
            continue

        if model is None:
            logger.error(f"❌ Impossibile inizializzare il modello {model_entry['name']}")
            continue

        model.eval()

        transform = transforms.Compose([
            transforms.Resize((model_entry["size"], model_entry["size"])),
            transforms.ToTensor(),
        ])
        input_tensor = transform(image_pil).unsqueeze(0)

        with torch.no_grad():
            output = model(input_tensor)

        # Anomaly map
        anomaly_map = (output.anomaly_map.cpu().squeeze().numpy() * 255).astype(np.uint8)
        anomaly_map_resized = cv2.resize(anomaly_map, (image_cv.shape[1], image_cv.shape[0]))
        
        # heatmap_color = cv2.applyColorMap(anomaly_map_resized, cv2.COLORMAP_JET)
        # overlay = cv2.addWeighted(image_cv, 0.6, heatmap_color, 0.4, 0)
        
        # Color anomaly map con overlay e contorni
        overlay = color_anomaly_map(anomaly_map_resized, image_cv)

        filename = f"anomalib_{model_name.lower()}_{uuid.uuid4().hex}.jpg"
        final_path = output_path / filename
        cv2.imwrite(str(final_path), overlay)
        logger.info(f"✅ Output {model_name} salvato in: {final_path}")
        paths.append(final_path)

    if not paths:
        return None
    return paths[0]  # oppure return all paths
