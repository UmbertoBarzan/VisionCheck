import cv2
import time
from pathlib import Path
from utils.logger import get_logger
import uuid
from utils.paths import DATA_DIR

logger = get_logger('camera')

def capture_image():
    filename = uuid.uuid4().hex + ".jpg"  # Genera un nome unico per l'immagine
    save_path = Path(DATA_DIR) / 'images' / filename  # Percorso dove salvare l'immagine
    save_path.parent.mkdir(parents=True, exist_ok=True)  # Crea la cartella se non esiste
    
    cap = cv2.VideoCapture(0)  # Usa la webcam predefinita
    
    if not cap.isOpened():
        logger.error("❌ Unable to access the camera")
        return None
    
    ret, frame = cap.read() # Legge un frame dalla webcam
    
    if not ret:
        logger.error("❌ Failed to capture image")
        cap.release()
        return None
    
    # Salva l'immagine catturata
    cv2.imwrite(str(save_path), frame)
    logger.info(f"✅ Image saved to {save_path}")
    cap.release()  # Rilascia la webcam
    return save_path
