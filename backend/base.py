from camera_ids import CameraIDS

def snap_unificato():
    cam = CameraIDS()
    cam.open_camera()
    frame = cam.snap()
    cam.close_camera()
    return frame
