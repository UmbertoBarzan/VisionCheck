from flask import Flask, send_from_directory, jsonify, send_file, request
import os
from dotenv import load_dotenv

from utils.paths import FRONTEND_DIR, DATASETS_DIR
from utils.logger import get_logger
from utils.paths import DATA_DIR

from pathlib import Path

from camera import capture_image
from yolo import run_yolo
from sam import run_sam

from anomalib_runner import train_enabled_models, run_anomalib


# Carica le variabili da .env (es. porta, debug mode)
load_dotenv()

# Inizializza il logger
logger = get_logger()

# Memorizza l'ultimo scatto per consentire anteprima e inferenze coerenti
last_captured_image: Path | None = None


def _capture_and_store_image() -> Path | None:
    """Effettua uno scatto e aggiorna il riferimento globale."""
    global last_captured_image
    image_path = capture_image()
    if image_path is not None and image_path.exists():
        last_captured_image = image_path
    return image_path


def _get_image(prefer_last: bool) -> Path | None:
    """Restituisce l'immagine da usare per l'inferenza.

    Se `prefer_last` è True prova ad usare l'ultimo scatto memorizzato,
    altrimenti ne effettua uno nuovo.
    """
    global last_captured_image

    if prefer_last and last_captured_image and last_captured_image.exists():
        logger.info(f"♻️  Using cached preview image: {last_captured_image.name}")
        return last_captured_image

    if prefer_last:
        logger.warning("⚠️ No cached preview available, capturing a fresh frame.")

    return _capture_and_store_image()

# Crea l'app Flask
app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path='')

# Rotta per servire il file index.html
@app.route('/')
def index():
    logger.info("✅ Serving index.html")
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/ping')
def ping():
    logger.info("Received ping request")
    return jsonify({"message": "pong"}), 200

@app.route('/api/preview')
def preview():
    image_path = _capture_and_store_image()

    if image_path is None or not image_path.exists():
        logger.error("❌ Unable to capture preview.")
        return jsonify({"error": "Preview capture failure"}), 500

    logger.info("✅ Preview ready, sending to frontend.")
    return send_file(image_path, mimetype='image/jpeg')


@app.route('/api/yolo-snapshot')
def yolo_snapshot():
    reuse_last = request.args.get('use_last', 'false').lower() == 'true'
    image_path = _get_image(reuse_last)

    if image_path is None or not image_path.exists():
        logger.error("❌ Unable to capture frame for YOLO.")
        return jsonify({"error": "Capture error"}), 500

    prediction_path = run_yolo(image_path)

    if prediction_path is None or not prediction_path.exists():
        logger.error("❌ YOLO inference failed.")
        return jsonify({"error": "YOLO inference error"}), 500

    logger.info("✅ YOLO snapshot ready, sending to frontend.")
    return send_file(prediction_path, mimetype='image/jpeg')

@app.route('/api/sam-snapshot')
def sam_snapshot():
    reuse_last = request.args.get('use_last', 'false').lower() == 'true'
    image_path = _get_image(reuse_last)

    if image_path is None:
        logger.error("❌ Unable to capture frame for SAM.")
        return jsonify({"error": "Capture error"}), 500

    prediction_path = run_sam(image_path)

    if prediction_path is None or not prediction_path.exists():
        logger.error("❌ SAM segmentation failed.")
        return jsonify({"error": "SAM inference error"}), 500

    logger.info("✅ SAM snapshot ready, sending to frontend.")
    return send_file(prediction_path, mimetype='image/jpeg')

@app.route('/api/anomalib_snapshot', methods=['GET', 'POST'])
def anomalib_snapshot():
    try:
        reuse_last = request.args.get('use_last', 'false').lower() == 'true'
        image_path = _get_image(reuse_last)

        if image_path is None:
            logger.error("❌ Unable to capture frame for Anomalib.")
            return jsonify({"error": "Capture error"}), 500

        prediction_path = run_anomalib(image_path)

        if prediction_path is None or not prediction_path.exists():
            logger.error("❌ Anomalib inference failed.")
            return jsonify({"error": "Anomalib inference error"}), 500

        logger.info("✅ Anomalib snapshot ready, sending to frontend.")
        return send_file(prediction_path, mimetype='image/jpeg')
    except Exception as e:
        logger.exception("❌ Anomalib error:")
        return jsonify({"error": str(e)}), 500



# Avvio dell'applicazione se eseguito direttamente
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))  # Usa la porta definita in .env o 5000 di default
    debug = os.getenv('DEBUG', 'true').lower() == 'true' # Usa il debug mode definito in .env o true di default
    logger.info(f"Starting VisionCheck on port {port} (debug={debug})")
    app.run(host='0.0.0.0', port=port, debug=debug)
