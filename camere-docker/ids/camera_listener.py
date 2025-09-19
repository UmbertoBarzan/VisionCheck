import zmq
import time
import os
from datetime import datetime

from ids_peak import ids_peak
from ids_peak_ipl import ids_peak_ipl
from ids_peak import ids_peak_ipl_extension

TARGET_PIXEL_FORMAT = ids_peak_ipl.PixelFormatName_BGRa8

class CameraListener:
    def __init__(self):
        print("🔧 Avvio CameraListener per IDS")

        self.serial = os.environ.get("CAMERA_SERIAL")
        if not self.serial:
            raise RuntimeError("❌ Variabile d'ambiente CAMERA_SERIAL non impostata")
        print(f"🔢 Serial target: {self.serial}")

        try:
            ids_peak.Library.Initialize()
            print("✅ Libreria IDS Peak inizializzata")
        except Exception as e:
            print(f"❌ Errore inizializzazione IDS Peak: {e}")
            raise

        context = zmq.Context()
        self.socket = context.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.IDENTITY, self.serial.encode())
        self.socket.connect("tcp://172.17.0.1:6000")

        # 📡 Registrazione iniziale
        self.socket.send_json({"event": "register", "serial": self.serial})

        # Stato interno
        self.device = None
        self.node_map = None
        self.datastream = None
        self.converter = None
        self.buffers = []
        self.running = False

        self.listen_loop()

    def listen_loop(self):
        while True:
            try:
                print("🔄 In attesa di comandi JSON ZMQ...")
                data = self.socket.recv_json()
                event = data.get("event", "").lower()

                print(f"📥 Comando JSON ricevuto: {event}")

                response = self._handle_event(event)
                if response:
                    self.socket.send_json({"event": response, "serial": self.serial})
            except Exception as e:
                print(f"❌ Errore loop ZMQ: {e}")
                self.socket.send_json({"event": "error", "serial": self.serial})
                time.sleep(1)

    def _handle_event(self, event: str) -> str:
        if event == 'added':
            print('camera registrata con successo')
            return
        if event == "init":
            return "Camera inizializzata" if self.open_camera() else "Errore init"
        elif event == "snap":
            path = self.snap()
            return f"Snap salvato: {path}" if path else "Snap fallito"
        elif event == "close":
            self.close_camera()
            return "Camera chiusa"
        elif event == "status":
            response = self.get_status()
            self.socket.send_json({"event": response, "serial": self.serial})
        else:
            return f"Evento sconosciuto: {event}"

    def open_camera(self) -> bool:
        try:
            print("🔍 Apertura camera con seriale:", self.serial)

            manager = ids_peak.DeviceManager.Instance()
            manager.Update()

            devices = manager.Devices()
            if not devices or devices.empty():
                print("❌ Nessun dispositivo trovato.")
                return False

            # Trova e apre la camera corretta usando il seriale
            for dev in devices:
                if dev.SerialNumber() == self.serial:
                    self.device = dev.OpenDevice(ids_peak.DeviceAccessType_Control)
                    print(f"✅ Dispositivo {self.serial} aperto con successo.")
                    break
            else:
                print("❌ Nessun dispositivo con quel seriale.")
                return False

            # Prende il NodeMap remoto e stampa alcune info utili
            self.node_map = self.device.RemoteDevice().NodeMaps()[0]

            try:
                print("📷 Modello:", self.node_map.FindNode("DeviceModelName").Value())
            except ids_peak.Exception:
                pass

            try:
                print("🧾 User ID:", self.node_map.FindNode("DeviceUserID").Value())
            except ids_peak.Exception:
                pass

            try:
                print("🧠 Sensore:", self.node_map.FindNode("SensorName").Value())
            except ids_peak.Exception:
                pass

            try:
                w = self.node_map.FindNode("WidthMax").Value()
                h = self.node_map.FindNode("HeightMax").Value()
                print(f"🖼️ Risoluzione max: {w}x{h}")
            except ids_peak.Exception:
                pass
            
            # Load the default settings
            self.node_map.FindNode("UserSetSelector").SetCurrentEntry("Default")
            self.node_map.FindNode("UserSetLoad").Execute()
            self.node_map.FindNode("UserSetLoad").WaitUntilDone()
            print('Default settings loaded')

            self.running = True
            return True

        except Exception as e:
            print(f"❌ Errore open_camera: {e}")
            return False

    def snap(self) -> str | None:
        if not self.device or not self.running:
            print("⚠️ Camera non inizializzata o non attiva.")
            return None

        try:
            print("📸 Avvio acquisizione immagine...")

            # Blocco i parametri
            self.node_map.FindNode("TLParamsLocked").SetValue(1)

            # Apro il datastream (se non già fatto)
            if not self.datastream:
                self.datastream = self.device.DataStreams()[0].OpenDataStream()

            # Alloco buffer se non ancora fatto
            if not self.buffers:
                payload_size = self.node_map.FindNode("PayloadSize").Value()
                min_buffers = self.datastream.NumBuffersAnnouncedMinRequired()
                for _ in range(min_buffers):
                    buf = self.datastream.AllocAndAnnounceBuffer(payload_size)
                    self.buffers.append(buf)

            for buf in self.buffers:
                self.datastream.QueueBuffer(buf)

            # Avvio acquisizione
            self.datastream.StartAcquisition()
            self.node_map.FindNode("AcquisitionStart").Execute()
            self.node_map.FindNode("AcquisitionStart").WaitUntilDone()

            # Eseguo trigger software
            self.node_map.FindNode("TriggerSoftware").Execute()
            self.node_map.FindNode("TriggerSoftware").WaitUntilDone()

            # Attendo immagine
            buffer = self.datastream.WaitForFinishedBuffer(2000)
            if buffer is None:
                print("❌ Nessun buffer ricevuto.")
                return None

            # Converto immagine
            img = ids_peak_ipl_extension.BufferToImage(buffer)
            width = self.node_map.FindNode("Width").Value()
            height = self.node_map.FindNode("Height").Value()
            pixfmt = ids_peak_ipl.PixelFormat(self.node_map.FindNode("PixelFormat").CurrentEntry().Value())

            if not self.converter:
                self.converter = ids_peak_ipl.ImageConverter()
                self.converter.PreAllocateConversion(pixfmt, TARGET_PIXEL_FORMAT, width, height)

            img_conv = self.converter.Convert(img, TARGET_PIXEL_FORMAT)

            # 📂 Crea sottocartella in RAM condivisa per la camera
            serial_dir = f"/shared/camera_{self.serial}"
            os.makedirs(serial_dir, exist_ok=True)

            # 🕓 Genera nome file con timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            filename = f"{serial_dir}/image_{timestamp}.png"

            # 💾 Salva immagine
            ids_peak_ipl.ImageWriter.WriteAsPNG(filename, img_conv)
            print(f"✅ Immagine salvata: {filename}")

            # 🔁 Rimetti il buffer in coda
            self.datastream.QueueBuffer(buffer)

            return filename

        except Exception as e:
            print(f"❌ Errore snap: {e}")
            return None


    def close_camera(self):
        try:
            if self.running:
                self.node_map.FindNode("AcquisitionStop").Execute()
                self.datastream.StopAcquisition(ids_peak.AcquisitionStopMode_Default)
                self.datastream.Flush(ids_peak.DataStreamFlushMode_DiscardAll)
                self.node_map.FindNode("TLParamsLocked").SetValue(0)
                self.running = False
            self.device.Close()
        except Exception as e:
            print(f"❌ Errore chiusura camera: {e}")

    def get_status(self) -> str:
        if self.device and self.running:
            return "READY"
        elif self.device:
            return "INITIALIZED_NO_ACQ"
        else:
            return "NOT_INITIALIZED"


if __name__ == "__main__":
    try:
        CameraListener()
    except KeyboardInterrupt:
        print("🛑 Interrotto da tastiera")
    except Exception as e:
        print(f"❌ Errore inizializzazione CameraListener: {e}")