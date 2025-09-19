import zmq
import json
import time
import docker
import subprocess
import os

def ensure_image_exists(image_name):
    try:
        client.images.get(image_name)
        print(f"✅ Immagine Docker '{image_name}' già presente.")
    except docker.errors.ImageNotFound:
        print(f"🔧 Immagine '{image_name}' non trovata. Avvio build...")
        logs = client.api.build(path=DOCKERFILE_PATH, tag=image_name, rm=True, decode=True)
        for chunk in logs:
            if "stream" in chunk:
                print(chunk["stream"], end="")
            elif "error" in chunk:
                print(f"❌ Errore build: {chunk['error']}")
                break
        print(f"\n✅ Build completata per '{image_name}'")
    except Exception as e:
        print(f"❌ Errore durante build immagine: {e}")
        
def start_device_watcher_compose():
    """
    Lancia il docker-compose con device_watcher.
    """
    ensure_image_exists(DOCKER_IMAGE)
    compose_file = os.path.join(DOCKERFILE_PATH, "docker-compose.yml")
    print("🚀 Avvio docker-compose per device_watcher...")
    try:
        subprocess.run(["docker-compose", "-f", compose_file, "up", "-d", "--build"], check=True)
        print("✅ Device watcher avviato con docker-compose")
    except subprocess.CalledProcessError as e:
        print(f"❌ Errore avvio docker-compose: {e}")
        
               
PORT = 6000
DOCKER_IMAGE = "visioncheck"
DOCKERFILE_PATH = "/home/umberto/Desktop/visioncheck/camere-docker/ids"
active_containers = {}
camera_idents = {}

# crea cartella condivisa in ram e lancia il docker compose per l'usb watcher
shm_path = "/dev/shm/visioncheck"
if not os.path.exists(shm_path):
    print(f"🔧 Creo memoria condivisa {shm_path}")
    subprocess.run(["sudo", "mkdir", "-p", shm_path])
    subprocess.run(["sudo", "mount", "-t", "tmpfs", "-o", "size=256M", "tmpfs", shm_path])
    

client = docker.from_env()


start_device_watcher_compose()

ctx = zmq.Context()
socket = ctx.socket(zmq.ROUTER)
socket.bind(f"tcp://*:{PORT}")

print(f"🌍 ROUTER bind: tcp://0.0.0.0:{PORT}")
print("📡 ROUTER in ascolto...")

def start_camera_container(serial):
    name = f"camera_{serial}"
    # ensure_image_exists(DOCKER_IMAGE)

    try:
        container = client.containers.get(name)
        if container.status == "running":
            print(f"⚠️ Container '{name}' già attivo")
            active_containers[serial] = name
            return
        else:
            print(f"♻️ Container '{name}' fermo, elimino...")
            container.remove(force=True)
    except docker.errors.NotFound:
        pass

    try:            
        container = client.containers.run(
            image=DOCKER_IMAGE,
            name=name,
            detach=True,
            privileged=True,
            devices=["/dev/bus/usb:/dev/bus/usb"],
            volumes={
                "/dev/bus/usb": {"bind": "/dev/bus/usb", "mode": "rw"},
                "/dev/shm/visioncheck": {"bind": "/shared", "mode": "rw"}
            },
            environment={"CAMERA_SERIAL": serial},
            command=["python3", "camera_listener.py"],
            tty=True,
            stdin_open=True,
        )
        active_containers[serial] = name
        print(f"✅ Avviato container: {name}")
    except Exception as e:
        print(f"❌ Errore avvio container: {e}")

def stop_camera_container(serial):
    name = active_containers.get(serial)
    if not name:
        print(f"⚠️ Nessun container per {serial}")
        return

    try:
        container = client.containers.get(name)
        container.remove(force=True)
        print(f"🛑 Rimosso container: {name}")
    except Exception as e:
        print(f"❌ Errore rimozione container: {e}")

    del active_containers[serial]

while True:
    try:
        ident, msg = socket.recv_multipart()

        try:
            data = json.loads(msg.decode())
        except json.JSONDecodeError:
            print(f"❌ Messaggio non JSON: {msg}")
            continue

        event = data.get("event")
        serial = data.get("serial")
        
        # 🔍 Se non è un comando, probabilmente è una risposta: log e salta
        if event is None:
            print(f"📭 Messaggio di risposta da {ident.decode(errors='ignore')}: {data}")
            continue

        print(f"📥 JSON da {ident.decode(errors='ignore')}: event={event}, serial={serial}")

        if event == "register":
            camera_idents[serial] = ident
            # print(f'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA {camera_idents}')
            socket.send_multipart([ident, json.dumps({"event": 'added', "msg": "camera registered"}).encode()])
        elif event == "attach":
            start_camera_container(serial)
            socket.send_multipart([ident, json.dumps({"event": "ok", "msg": "camera attached"}).encode()])
        elif event == "detach":
            stop_camera_container(serial)
            socket.send_multipart([ident, json.dumps({"event": "ok", "msg": "camera detached"}).encode()])
        elif event == 'Camera inizializzata':
            print(event)
        elif 'Snap salvato:' in event:
            print(event)
        elif event == 'Camera chiusa':
            print(event)
        elif event in ["init", "snap", "close", "status"]:
            camera_ident = camera_idents.get(serial)
            if not camera_ident:
                print(f"❌ Nessuna camera registrata con serial {serial}")
                continue

            socket.send_multipart([camera_ident, json.dumps(data).encode()])

            # Attendi risposta (600ms)
            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)
            socks = dict(poller.poll(800))
            if socket in socks:
                ident, msg = socket.recv_multipart()
                try:
                    data = json.loads(msg.decode())
                except json.JSONDecodeError:
                    print(f"❌ Messaggio non JSON: {msg}")
                    continue
                
                event = data.get("event")
                serial = data.get("serial")
                print(f"📬 Risposta da {serial}: {event}")
            else:
                print(f"⏱️ Nessuna risposta dalla camera {serial}")
        else:
            print(f"⚠️ Evento sconosciuto: {event}")

    except KeyboardInterrupt:
        print("🛑 Interrotto. Chiudo container...")
        for serial in list(active_containers.keys()):
            stop_camera_container(serial)
        break
    except Exception as e:
        print(f"❌ Errore generale: {e}")
        time.sleep(1)