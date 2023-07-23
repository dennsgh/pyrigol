import json
from device.dg4202 import DG4202, DG4202Detector, DG4202Mock
from datetime import datetime, timedelta
import time
from features.scheduler import Scheduler
from pathlib import Path
import os

DG4202_MOCK_DEVICE = DG4202Mock()
SCHEDULER = Scheduler()
JSON_FILE = Path(os.getenv("DATA"), "state.json")

# we use a JSON file this to prevent conflicts when using global variables between different user accesses.
app_start_time = time.time()


def read_state():
    """
    Function to read state from a JSON file. 
    If the file doesn't exist or is empty, it returns a default state.

    Returns:
        dict: A dictionary containing state variables.
    """
    try:
        if JSON_FILE.stat().st_size > 0:
            with open(JSON_FILE, 'r') as f:
                state = json.load(f)
                return state
        else:
            return {"last_known_device_uptime": None, "dg4202_device": None}
    except (FileNotFoundError, ValueError):
        return {"last_known_device_uptime": None, "dg4202_device": None}


def write_state(state):
    """
    Function to write state to a JSON file.

    Args:
        state (dict): A dictionary containing state variables.
    """
    with open(JSON_FILE, 'w') as f:
        json.dump(state, f)


def get_uptime():
    """
    Function to get uptime from last known device uptime.

    Returns:
        str: Uptime in HH:MM:SS format if known, otherwise 'N/A'.
    """
    uptime_seconds = time.time() - app_start_time
    uptime_str = str(timedelta(seconds=int(uptime_seconds)))
    return uptime_str


def create_dg4202(args_dict: dict) -> DG4202:
    """
    Function to create a DG4202 device. 
    Updates the state depending on the device creation.

    Args:
        args_dict (dict): Dictionary of arguments.

    Returns:
        DG4202: A DG4202 device object.
    """
    state = read_state()
    if args_dict['hardware_mock']:
        if DG4202_MOCK_DEVICE.killed:
            # Simulate dead device
            state["last_known_device_uptime"] = None
            write_state(state)
            return None
        else:
            if state["last_known_device_uptime"] is None:
                state["last_known_device_uptime"] = time.time()
            write_state(state)
            return DG4202_MOCK_DEVICE
    else:
        dg4202_device = DG4202Detector().detect_device()
        if dg4202_device is None:
            state["last_known_device_uptime"] = None  # Reset the uptime
        else:
            if state["last_known_device_uptime"] is None:
                state["last_known_device_uptime"] = time.time()
        state["dg4202_device"] = dg4202_device
        write_state(state)
        return dg4202_device


def get_device_uptime(args_dict: dict):
    """
    Function to get device uptime from last known device uptime.

    Args:
        args_dict (dict): Dictionary of arguments.

    Returns:
        str: Uptime in HH:MM:SS format if known, otherwise 'N/A'.
    """
    state = read_state()
    if state["last_known_device_uptime"]:
        uptime_seconds = time.time() - state["last_known_device_uptime"]
        uptime_str = str(timedelta(seconds=int(uptime_seconds)))
        return uptime_str
    else:
        return "N/A"
