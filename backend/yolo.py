from ultralytics import YOLO
from pathlib import Path
from utils.logger import get_logger
import uuid
from utils.paths import DATA_DIR, MODELS_DIR
import cv2
import os

logger = get_logger('yolo')

# carica il modello una volta sola per evitare di ricaricarlo ad ogni richiesta

try:
    model = YOLO(MODELS_DIR / 'yolov8n.pt')
    logger.info(f"✅ Yolo model loaded")
except Exception as e:
    logger.error(f"❌ Failed to load model {e}")
    model = None
    
def run_yolo(image_path: Path) -> Path | None:
    '''Esegue il modello YOLO su un'immagine e salva i risultati.'''
    if model is None:
        logger.error("❌ YOLO model is not loaded, cannot run detection.")
        return None
    try:
        results = model.predict(source=str(image_path), save=True, save_txt=True, save_conf=True)
    except Exception as e:
        logger.error(f"Errore durante la predizione: {e}")
        return None
    
    # save
    annotated = results[0].plot() # save the image with bounding boxes
    output_name = f'yolo_{uuid.uuid4().hex}.jpg'
    output_path = DATA_DIR / 'yolo' / output_name
    os.makedirs(output_path.parent, exist_ok=True)  # Assicura che la cartella yolo esista
    cv2.imwrite(str(output_path), annotated)
    logger.info(f"✅ YOLO detection completed, results saved to {output_path}")
    return output_path