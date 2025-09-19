from ids_peak import ids_peak
from ids_peak_ipl import ids_peak_ipl
import numpy as np

class CameraIDS:
    def __init__(self, index: int = 0) -> bool:
        print("🔧 Inizializzo libreria IDS Peak (host)")
        ids_peak.Library.Initialize()

        self.device = None
        self.datastream = None
        self.node_map = None
        self.image_node_map = None
        self.running = False

    def open_camera(self) -> bool:
        # initialize library
        ids_peak.Library.Initialize()

        # create a device manager object
        self.device_manager = ids_peak.DeviceManager.Instance()

        try:
            # update the device manager
            self.device_manager.Update()

            # exit program if no device was found
            if self.device_manager.Devices().empty():
                print("No device found. Exiting Program.")
                return

            # list all available devices
            for i, self.device in enumerate(self.device_manager.Devices()):
                print(str(i) + ": " + self.device.ModelName() + " ("
                    + self.device.ParentInterface().DisplayName() + "; "
                    + self.device.ParentInterface().ParentSystem().DisplayName() + "v."
                    + self.device.ParentInterface().ParentSystem().Version() + ")")

            # select a device to open
            selected_device = None
            while True:
                try:
                    selected_device = int(input("Select device to open: "))
                    if selected_device in range(len(self.device_manager.Devices())):
                        break
                    else:
                        print("Invalid ID.")
                except ValueError:
                    print("Please enter a correct id.")
                    continue

            # open selected device
            self.device = self.device_manager.Devices()[selected_device].OpenDevice(ids_peak.DeviceAccessType_Control)

            # get the remote device node map
            nodemap_remote_device = self.device.RemoteDevice().NodeMaps()[0]

            # print model name and user ID
            print("Model Name: " + nodemap_remote_device.FindNode("DeviceModelName").Value())
            try:
                print("User ID: " + nodemap_remote_device.FindNode("DeviceUserID").Value())
            except ids_peak.Exception:
                print("User ID: (unknown)")

            # print sensor information, not knowing if device has the node "SensorName"
            try:
                print("Sensor Name: " + nodemap_remote_device.FindNode("SensorName").Value())
            except ids_peak.Exception:
                print("Sensor Name: " + "(unknown)")

            # print resolution
            try:
                print("Max. resolution (w x h): "
                    + str(nodemap_remote_device.FindNode("WidthMax").Value()) + " x "
                    + str(nodemap_remote_device.FindNode("HeightMax").Value()))
            except ids_peak.Exception:
                print("Max. resolution (w x h): (unknown)")

        except Exception as e:
            print("Exception: " + str(e) + "")

        finally:
            input("Press Enter to continue...")
            ids_peak.Library.Close()
    
    def snap(self):
        # (stesso codice di prima)
        ...
    
    def close_camera(self):
        ...
    
    def get_status(self):
        ...


cam = CameraIDS()
if cam.open_camera():
    print("Camera aperta con successo!")
else:
    print("Errore nell'apertura della camera.")