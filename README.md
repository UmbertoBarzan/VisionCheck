# VisionCheck

VisionCheck è un playground di computer vision che combina tre modelli diversi per analizzare un frame acquisito dalla webcam:

- **YOLOv8** per il rilevamento oggetti con bounding box.
- **SAM (Segment Anything)** per la segmentazione delle regioni d'interesse.
- **Anomalib (Padim)** per l'anomaly detection rispetto a un dataset di pezzi "buoni".

Il backend è una semplice app Flask che espone le API per acquisire un'anteprima, lanciare l'inferenza e restituire le immagini annotate. Il frontend statico mostra un'interfaccia per scegliere il modello e visualizzare rapidamente i risultati.

## Requisiti

- Python 3.10 (consigliato l'uso di Conda o di un virtualenv)
- Webcam accessibile da OpenCV
- Modelli pre-addestrati salvati in `backend/models/`:
  - `yolov8n.pt`
  - `sam_vit_b.pth`
  - Checkpoint Anomalib in `results/Padim/hazelnut_toy/latest/weights/lightning/model.ckpt`

## Installazione

1. **Crea e attiva l'ambiente** (esempio con Conda):
   ```bash
   conda create -n visioncheck python=3.10
   conda activate visioncheck
   ```
2. **Installa le dipendenze Python**:
   ```bash
   pip install -r requirements.txt
   ```
3. **(Opzionale) Imposta le variabili d'ambiente** in un file `.env` (es. porta http, modalità debug):
   ```env
   PORT=5000
   DEBUG=true
   ```

## Avvio

```bash
python backend/app.py
```

L'applicazione espone il frontend all'indirizzo [http://localhost:5000](http://localhost:5000).

## Come funziona l'interfaccia

1. **Acquisisci l'anteprima**: il sito scatta un frame dalla webcam e lo mostra, così puoi verificare l'inquadratura.
2. **Scegli un modello**: YOLO, SAM o Anomalib useranno l'ultimo frame acquisito per produrre l'immagine annotata.
3. **Scarica o salva i risultati**: i file sono salvati anche su disco nelle cartelle `data/yolo`, `data/sam` e `data/anomalib`.

## Struttura del progetto

```
backend/             # Flask app, logica di acquisizione e inferenza
frontend/            # Pagina HTML/CSS/JS servita da Flask
configs/             # Configurazioni (es. modelli anomalib abilitati)
results/             # Checkpoint addestrati con anomalib
datasets/            # Dataset per training / evaluation anomalib
```

## Note e troubleshooting

- Se YOLO o SAM non partono, verifica che i pesi siano nella cartella `backend/models/` e che PyTorch sia installato (CPU o GPU a seconda della macchina).
- Per Anomalib è necessario avere un checkpoint valido collegato alla cartella `latest/` (il progetto include un esempio Padim). Senza di esso l'endpoint restituisce errore 500.
- In ambienti con permessi restrittivi potrebbe essere necessario creare manualmente `~/.config/Ultralytics/` per permettere a Ultralytics di salvare le proprie impostazioni.

Buon divertimento con VisionCheck! :camera_flash:
