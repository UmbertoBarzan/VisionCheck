import zmq

ctx = zmq.Context()
socket = ctx.socket(zmq.DEALER)
socket.setsockopt(zmq.IDENTITY, b"manual_tester")
socket.connect("tcp://172.17.0.1:6000")

while True:
    try:
        cmd = input("📤 Comando (init/snap/status/close/exit): ").strip().lower()
        if cmd == "exit":
            break
        socket.send_json({"event": cmd, "serial": "4108618466"})
    except KeyboardInterrupt:
        break
