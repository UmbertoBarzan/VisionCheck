import zmq
import json
import sys
from ids_peak import ids_peak


sys.stdout.reconfigure(line_buffering=True)

ZMQ_ROUTER_ADDRESS = "tcp://172.17.0.1:6000"  # IP host docker bridge

class DeviceWatcher:
    def __init__(self):
        print("🔎 Avvio DeviceWatcher IDS...")

        ids_peak.Library.Initialize()
        self.device_manager = ids_peak.DeviceManager.Instance()

        # 🔌 ZMQ DEALER → connessione al ROUTER
        ctx = zmq.Context()
        self.socket = ctx.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.IDENTITY, b"device_watcher")
        self.socket.connect(ZMQ_ROUTER_ADDRESS)

        # 🧠 Mappa temporanea key → serial per recuperare serial nel 'lost'
        self.device_keys = {}

        # 📡 Poller per leggere eventuali risposte (non bloccante)
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

        # 🔁 Registra callback
        self.register_callbacks()

        # ⚠️ Almeno una chiamata iniziale a .Update() per attivare eventi
        self.device_manager.Update()

    def register_callbacks(self):
        self.device_found_callback = self.device_manager.DeviceFoundCallback(self.device_found)
        self.device_manager.RegisterDeviceFoundCallback(self.device_found_callback)

        self.device_lost_callback = self.device_manager.DeviceLostCallback(self.device_lost)
        self.device_manager.RegisterDeviceLostCallback(self.device_lost_callback)

    def device_found(self, device):
        try:
            serial = device.Property(ids_peak.DevicePropertyKey_SerialNumber).ToString()
            key = device.Key()

            self.device_keys[key] = serial  # Salva associazione key → serial

            print(f"🟢 Camera collegata: {serial}")
            self.send_event("attach", serial)

        except Exception as e:
            print(f"❌ Errore in device_found: {e}")

    def device_lost(self, key):
        serial = self.device_keys.pop(key, None)
        if serial:
            print(f"🔴 Camera scollegata: {serial}")
            self.send_event("detach", serial)
        else:
            print(f"🔴 Camera scollegata (seriale sconosciuto): Key={key}")

    def send_event(self, event_type, serial):
        msg = {
            "event": event_type,
            "serial": serial
        }

        self.socket.send_json(msg)

        # 📭 Aspetta risposta breve (max 300 ms)
        socks = dict(self.poller.poll(300))
        if self.socket in socks:
            try:
                reply = self.socket.recv_json()
                print(f"📬 Risposta dal ROUTER: {reply.get('msg')}")
            except Exception as e:
                print(f"⚠️ Errore nella risposta ZMQ: {e}")

    def run(self):
        print("📡 DeviceWatcher pronto. Ctrl+C per uscire.")
        try:
            while True:
                pass  # Lascia il processo vivo per ricevere eventi
        except KeyboardInterrupt:
            print("🛑 Interrotto da tastiera.")
        finally:
            ids_peak.Library.Close()


if __name__ == "__main__":
    watcher = DeviceWatcher()
    watcher.run()
