import json
from device.dg4202 import DG4202, DG4202Detector, DG4202Mock
from api.dg4202_api import DG4202APIServer
from datetime import datetime, timedelta
import time
from features.scheduler import Scheduler
from features.state_managers import StateManager, DG4202Manager, DG4202APIManager
from pathlib import Path
import os
import threading

#DG4202_MOCK_DEVICE = DG4202Mock()
STATE_FILE = Path(os.getenv("DATA"), "state.json")

app_start_time = time.time()
# ================================== Place holder globals, these are initialized in app.py
state_manager: StateManager = None
dg4202_manager: DG4202Manager = None
api_manager: DG4202APIManager = None
DG4202SCHEDULER: Scheduler = None
# ==================================