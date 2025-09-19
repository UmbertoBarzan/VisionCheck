import time
import zmq
import json
from ids_peak import ids_peak
import sys


sys.stdout.reconfigure(line_buffering=True)


CHECK_INTERVAL = 1.0  # secondi tra i controlli
ZMQ_ROUTER_ADDRESS = "tcp://172.17.0.1:6000"  # IP host docker bridge
print("✅ Libreria IDS Peak inizializzata")

class DeviceWatcher:
    def __init__(self):
        print("🔎 Avvio DeviceWatcher IDS...")
        
        ids_peak.Library.Initialize()


        self.known_serials = set()

        # 🔌 ZMQ DEALER → connessione al ROUTER
        ctx = zmq.Context()
        self.socket = ctx.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.IDENTITY, b"device_watcher")
        self.socket.connect(ZMQ_ROUTER_ADDRESS)
        
        # 📡 Poller per eventuali risposte (finestra non bloccante)
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

    def check_devices(self):
        """
        Controlla quali seriali sono collegati e individua cambiamenti.
        """
        manager = ids_peak.DeviceManager.Instance()
        manager.Update()

        current_serials = set()
        for dev in manager.Devices():
            current_serials.add(dev.SerialNumber())

        # 🔁 Confronta con seriali già noti
        added = current_serials - self.known_serials
        removed = self.known_serials - current_serials

        for serial in added:
            print(f"🟢 Camera collegata: {serial}")
            self.send_event("attach", serial)

        for serial in removed:
            print(f"🔴 Camera scollegata: {serial}")
            self.send_event("detach", serial)

        self.known_serials = current_serials

    def send_event(self, event_type, serial):
        """
        Invia evento al router via ZMQ.
        """
        msg = {
            "event": event_type,
            "serial": serial
        }
        
        self.socket.send_json(msg)

        # 📭 Attendi risposta breve (300ms)
        socks = dict(self.poller.poll(300))
        if self.socket in socks:
            reply = self.socket.recv_json()
            event = reply.get('event')
            msg = reply.get('msg')
            print(f"📬 Risposta dal ROUTER: {msg}")

    def run(self):
        """
        Loop principale.
        """
        start = time.time()
        try:
            while True:
                self.check_devices()
                time.sleep(CHECK_INTERVAL)
                # if time.time() - start > 5:
                #     break
        except KeyboardInterrupt:
            print("🛑 Interrotto da tastiera.")
        finally:
            ids_peak.Library.Close()

if __name__ == "__main__":
    watcher = DeviceWatcher()
    watcher.run()