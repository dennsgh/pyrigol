from device.dg4202 import DG4202, DG4202Detector, DG4202MockInterface, DG4202StateMachine
from datetime import datetime, timedelta
import time

DG4202_FSM = DG4202StateMachine()
DG4202_MOCK_INTERFACE = DG4202MockInterface(DG4202_FSM)
DG4202_MOCK_DEVICE = DG4202(DG4202_MOCK_INTERFACE)

# Track the start time
start_time = time.time()
last_known_device_uptime = None


def get_uptime():
    """
    Returns a string representing the current uptime in the format "HH:MM:SS".
    """
    uptime_seconds = time.time() - start_time
    uptime_str = str(timedelta(seconds=int(uptime_seconds)))
    return uptime_str


def get_device_uptime():
    if last_known_device_uptime:
        uptime_seconds = time.time() - last_known_device_uptime
        uptime_str = str(timedelta(seconds=int(uptime_seconds)))
        return uptime_str
    else:
        return "N/A"


def create_dg4202(args_dict: dict) -> DG4202:
    if args_dict['hardware_mock']:
        if DG4202_MOCK_INTERFACE.killed:
            # simulate dead device
            # kill it using the --api-server feature using REST API
            return None
        else:
            return DG4202_MOCK_DEVICE
    else:
        return DG4202Detector().detect_device()