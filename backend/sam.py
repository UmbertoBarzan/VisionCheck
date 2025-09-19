import cv2
import numpy as np
import uuid
from pathlib import Path
import os

from utils.paths import MODELS_DIR, DATA_DIR
from utils.logger import get_logger

from segment_anything import sam_model_registry, SamAutomaticMaskGenerator

logger = get_logger('sam')

try:
    sam = sam_model_registry["vit_b"](checkpoint=str(MODELS_DIR / "sam_vit_b.pth"))
    mask_generator = SamAutomaticMaskGenerator(
        model=sam,
        points_per_side=8,           # Di default è 32 (molto pesante)
        pred_iou_thresh=0.88,
        stability_score_thresh=0.95,
        crop_n_layers=0,             # Evita i crop multi-scala (più leggeri)
    )
    
    logger.info("✅ SAM model loaded successfully")
except Exception as e:
    logger.error(f"❌ Failed to load SAM model: {e}")
    sam = None
    mask_generator = None
    
def run_sam(image_path: Path) -> Path | None:
    '''Esegue il modello SAM su un'immagine e salva i risultati.'''
    
    
    if mask_generator is None:
        logger.error("SAM non è stato inizializzato.")
        return None
    
    image = cv2.imread(str(image_path)) # Legge l'immagine da file
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # Converte da BGR a RGB per SAM
        
    if image is None:
        logger.error(f"❌ Impossibile leggere l'immagine da {image_path}")
        return None
    
    try:
        masks = mask_generator.generate(image)
        logger.info(f"✅ {len(masks)} masks generated")
    except Exception as e:
        logger.error(f"❌ Errore durante la generazione delle maschere: {e}")
        return None
    
    
    annotated = image.copy()
    for mask in masks:
        seg = mask['segmentation'] # Crea una maschera binaria
        contours, _ = cv2.findContours(seg.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(annotated, contours, -1, (0, 255, 0), 1)  # verde
        
        filename = f"sam_{uuid.uuid4().hex}.jpg"
        os.makedirs(DATA_DIR / 'sam', exist_ok=True)  # Assicura che la cartella esista
        output_path = DATA_DIR / 'sam' / filename
        cv2.imwrite(str(output_path), annotated)
        logger.info(f"Salvato risultato SAM in: {output_path.name}")
        return output_path   