from camera_ids import CameraIDS

class CameraManager:
    def __init__(self):
        self.cameras = []

    def add_camera(self):
        cam = CameraIDS()
        cam.open_camera()
        self.cameras.append(cam)
