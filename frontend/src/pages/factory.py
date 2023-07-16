from device.dg4202 import DG4202, DG4202Detector, DG4202Mock
from datetime import datetime, timedelta
import time

# Track the start time
start_time = time.time()
last_known_device_uptime = None
dg4202_device = None

DG4202_MOCK_DEVICE = DG4202Mock()


def get_uptime():
    """
    Returns a string representing the current uptime in the format "HH:MM:SS".
    """
    uptime_seconds = time.time() - start_time
    uptime_str = str(timedelta(seconds=int(uptime_seconds)))
    return uptime_str


def create_dg4202(args_dict: dict) -> DG4202:
    global dg4202_device
    global last_known_device_uptime  # To set the start of the uptime

    if args_dict['hardware_mock']:
        if DG4202_MOCK_DEVICE.killed:
            # Simulate dead device
            last_known_device_uptime = None
            return None
        else:
            if last_known_device_uptime is None:
                last_known_device_uptime = time.time()
            return DG4202_MOCK_DEVICE
    else:
        dg4202_device = DG4202Detector().detect_device()
        if dg4202_device is None:
            last_known_device_uptime = None  # Reset the uptime
        else:
            if last_known_device_uptime is None:
                last_known_device_uptime = time.time()
        return dg4202_device


def get_device_uptime(args_dict: dict):
    global last_known_device_uptime
    if last_known_device_uptime:
        uptime_seconds = time.time() - last_known_device_uptime
        uptime_str = str(timedelta(seconds=int(uptime_seconds)))
        return uptime_str
    else:
        return "N/A"
