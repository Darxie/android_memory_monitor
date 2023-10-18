from uiautomator import Device
from utils import Utils


def lel():
    device = Device(Utils().get_device_id())
    print("connected to device")
    device.screen.on()
    print(device.info)
    device.swipe(500, 1400, 500, 300)
    device.swipe(500, 1600, 500, 300)
    device.swipe(500, 1800, 500, 300)
    exists = device(text="Sygic Truck Debug").exists
    if exists:
        device(text="Sygic Truck Debug").click()
    # device(text="Settings").swipe.up()


if __name__ == "__main__":
    lel()
    print("finished")
