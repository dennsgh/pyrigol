import json
from device.dg4202 import DG4202, DG4202Detector, DG4202Mock
from datetime import datetime, timedelta
import time
from features.scheduler import Scheduler, FunctionMap
from pathlib import Path
import os


class StateManager:

    def __init__(self, json_file: Path = None):
        self.json_file = json_file or Path(os.getenv("DATA"), "state.json")
        self.birthdate = time.time()

    def read_state(self) -> dict:
        try:
            if self.json_file.stat().st_size > 0:
                with open(self.json_file, 'r') as f:
                    return json.load(f)
            else:
                return {"last_known_device_uptime": None}
        except (FileNotFoundError, ValueError):
            return {"last_known_device_uptime": None}

    def write_state(self, state: dict):
        with open(self.json_file, 'w') as f:
            json.dump(state, f)

    def get_uptime(self):
        """
        Function to get uptime from last known device uptime.

        Returns:
            str: Uptime in HH:MM:SS format if known, otherwise 'N/A'.
        """
        uptime_seconds = time.time() - self.birthdate
        uptime_str = str(timedelta(seconds=int(uptime_seconds)))
        return uptime_str


class DG4202Manager:

    def __init__(self, state_manager: StateManager, args_dict: dict):
        self.state_manager = state_manager
        self.args_dict = args_dict
        self._mock_device = DG4202Mock()
        self._initialize_device()
        self.function_map = self._initialize_function_map()  # required for scheduler

    def _initialize_device(self):
        if self.args_dict['hardware_mock']:
            self.dg4202_device = self._mock_device
        else:
            self.dg4202_device = DG4202Detector.detect_device()

    def _output_on_off_wrapper(self, *args, **kwargs):
        if not self.dg4202_device.is_connection_alive():
            # Log the disconnection
            print(f"Device is disconnected at {datetime.now()}")
            return None
        return self.dg4202_device.output_on_off(*args, **kwargs)

    def _initialize_function_map(self) -> FunctionMap:
        # Use wrapper methods in function map
        function_map = FunctionMap(id="dg4202_function_map")
        function_map.register("TURN_ON_CH1",
                              self._output_on_off_wrapper,
                              default_kwargs={
                                  'channel': 1,
                                  'status': True
                              })
        function_map.register("TURN_ON_CH2",
                              self._output_on_off_wrapper,
                              default_kwargs={
                                  'channel': 2,
                                  'status': True
                              })
        function_map.register("TURN_OFF_CH1",
                              self._output_on_off_wrapper,
                              default_kwargs={
                                  'channel': 1,
                                  'status': False
                              })
        function_map.register("TURN_OFF_CH2",
                              self._output_on_off_wrapper,
                              default_kwargs={
                                  'channel': 2,
                                  'status': False
                              })
        return function_map

    def create_dg4202(self) -> DG4202:
        """
        Function to create a DG4202 device. 
        Updates the state depending on the device creation.

        Args:
            args_dict (dict): Dictionary of arguments.

        Returns:
            DG4202: A DG4202 device object.
        """
        state = self.state_manager.read_state()
        if self.args_dict['hardware_mock']:
            if self._mock_device.killed:
                # Simulate dead device
                state["last_known_device_uptime"] = None
                self.state_manager.write_state(state)
                return None
            else:
                if state["last_known_device_uptime"] is None:
                    state["last_known_device_uptime"] = time.time()
                self.state_manager.write_state(state)
                self.dg4202_device = self._mock_device
                return self.dg4202_device
        else:
            self.dg4202_device = DG4202Detector().detect_device()
            if self.dg4202_device is None:
                state["last_known_device_uptime"] = None  # Reset the uptime
            else:
                if state["last_known_device_uptime"] is None:
                    state["last_known_device_uptime"] = time.time()
            self.state_manager.write_state(state)
            return self.dg4202_device

    def get_device_uptime(self, args_dict: dict):
        """
        Function to get device uptime from last known device uptime.

        Args:
            args_dict (dict): Dictionary of arguments.

        Returns:
            str: Uptime in HH:MM:SS format if known, otherwise 'N/A'.
        """
        state = self.state_manager.read_state()
        if state["last_known_device_uptime"]:
            uptime_seconds = time.time() - state["last_known_device_uptime"]
            uptime_str = str(timedelta(seconds=int(uptime_seconds)))
            return uptime_str
        else:
            return "N/A"
