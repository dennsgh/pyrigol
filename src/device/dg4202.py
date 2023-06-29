from flask import Flask, request, jsonify
from flask.wrappers import Response
import pyvisa
import abc
import re
from typing import Optional, Union, List, Tuple
from werkzeug.exceptions import HTTPException
from threading import Thread
import os
import signal


class DG4202Detector:

    @staticmethod
    def detect_device() -> Optional['DG4202']:
        """
        Static method that attempts to detect a DG4202 device connected via TCP/IP or USB.
        Loops through all available resources, attempting to open each one and query its identity.
        If a DG4202 device is found, it creates and returns a DG4202 instance.

        Returns:
            DG4202: An instance of the DG4202 class connected to the detected device, 
                    or None if no such device is found.
        """
        rm = pyvisa.ResourceManager()
        resources = rm.list_resources()

        for resource in resources:
            if re.match("^TCPIP", resource):
                try:
                    device = rm.open_resource(resource)
                    idn = device.query("*IDN?")
                    if "DG4202" in idn:
                        return DG4202(DG4202Ethernet(resource.split('::')[1]))
                except pyvisa.errors.VisaIOError:
                    pass
            elif re.match("^USB", resource):
                try:
                    device = rm.open_resource(resource)
                    idn = device.query("*IDN?")
                    if "DG4202" in idn:
                        return DG4202(DG4202USB(resource))
                except pyvisa.errors.VisaIOError:
                    pass

        print("No DG4202 device found.")
        return None


class DG4202Interface(abc.ABC):

    @abc.abstractmethod
    def write(self, command: str) -> None:
        """
        Abstract method for writing a command to the interface.

        Args:
            command (str): The command to be written.
        """
        pass

    @abc.abstractmethod
    def read(self, command: str) -> str:
        """
        Abstract method for reading a response from the interface.

        Args:
            command (str): The command to be sent for reading.

        Returns:
            str: The response received from the interface.
        """
        pass


class DG4202Ethernet(DG4202Interface):

    def __init__(self, ip_address: str):
        rm = pyvisa.ResourceManager()
        self.inst = rm.open_resource(f'TCPIP::{ip_address}::INSTR')

    def write(self, command: str) -> None:
        self.inst.write(command)

    def read(self, command: str) -> str:
        return self.inst.query(command)


class DG4202USB(DG4202Interface):

    def __init__(self, resource_name: str):
        rm = pyvisa.ResourceManager()
        self.inst = rm.open_resource(resource_name)

    def write(self, command: str) -> None:
        self.inst.write(command)

    def read(self, command: str) -> str:
        return self.inst.query(command)


class DG4202:

    @staticmethod
    def available_waveforms() -> List[str]:
        """
        Returns a list of available waveform types.

        Returns:
            List[str]: List of available waveform types.
        """
        return ['SIN', 'SQUARE', 'RAMP', 'PULSE', 'NOISE', 'ARB', 'DC']

    @staticmethod
    def available_modes() -> List[str]:
        """
        Returns a list of available modes.

        Returns:
            List[str]: List of available modes.
        """
        return ['off', 'sweep', 'burst', 'mod']

    def __init__(self, interface: DG4202Interface):
        self.interface = interface

    def set_waveform(self,
                     channel: int,
                     waveform_type: str = None,
                     frequency: float = None,
                     amplitude: float = None,
                     offset: float = None) -> None:
        """
        Generates a waveform with the specified parameters. If a parameter is None, its current value is left unchanged.

        Args:
            waveform_type (str, optional): The type of waveform to generate. Defaults to None.
            frequency (float, optional): The frequency of the waveform in Hz. Defaults to None.
            amplitude (float, optional): The amplitude of the waveform. Defaults to None.
            offset (float, optional): The offset of the waveform. Defaults to None.
        """
        if waveform_type is not None:
            self.interface.write(f"SOURce{channel}:FUNCtion {waveform_type}")
        if frequency is not None:
            self.interface.write(f"SOURce{channel}:FREQuency:FIXed {frequency}")
        if amplitude is not None:
            self.interface.write(f"SOURce{channel}:VOLTage:LEVel:IMMediate:AMPLitude {amplitude}")
        if offset is not None:
            self.interface.write(f"SOURce{channel}:VOLTage:LEVel:IMMediate:OFFSet {offset}")

    def turn_off_modes(self, channel: int) -> None:
        """
        Turns off all modes (sweep, burst, modulation) on the device.
        """
        self.interface.write(f"SOURce{channel}:SWEEp:STATe OFF")
        self.interface.write(f"SOURce{channel}:BURSt:STATe OFF")
        self.interface.write(f"SOURce{channel}:MOD:STATe OFF")

    def check_status(self) -> str:
        """
        Checks the status of the device.

        Returns:
            str: The status of the device.
        """
        return self.interface.read("*STB?")

    def output_on_off(self, channel: int, status: bool) -> None:
        """
        Turns the output of the device on or off.

        Args:
            status (bool): True to turn on the output, False to turn it off.
        """
        command = f"OUTPut{channel} ON" if status else f"OUTPut{channel} OFF"
        self.interface.write(command)

    def set_mode(self, channel: int, mode: str, mod_type: str = None) -> None:
        """
        Sets the mode of the device.

        Args:
            mode (str): The mode to set. Supported values: 'sweep', 'burst', 'mod', 'off'.
            mod_type (str, optional): The modulation type. Required when mode is 'mod'. Defaults to None.
        """
        if mode.lower() == "sweep":
            self.interface.write(f"SOURce{channel}:SWEEp:STATe ON")
        elif mode.lower() == "burst":
            self.interface.write(f"SOURce{channel}:BURSt:STATe ON")
        elif mode.lower() == "mod":
            self.interface.write(f"SOURce{channel}:MOD:STATe ON")
            if mod_type:
                self.interface.write(f"SOURce{channel}:MOD:TYPE {mod_type}")
        elif mode.lower() == "off":
            self.turn_off_modes(channel)
        else:
            print("Unsupported mode. Please use 'sweep', 'burst', or 'mod'")

    def set_modulation_mode(self, channel: int, mod_type: str, mod_params: dict):
        """
        Sets the device to modulation mode with the specified parameters.

        Args:
            channel (int): The output channel to set.
            mod_type (str): The type of modulation to apply.
            mod_params (dict): Dictionary of parameters for modulation mode.
                Expected keys are 'SOUR', 'DEPT', 'DEV', 'RATE' etc.
        """
        self.interface.write(f"SOURce{channel}:MOD:STATe ON")
        self.interface.write(f"SOURce{channel}:MOD:TYPE {mod_type}")
        for param in ['SOUR', 'DEPT', 'DEV', 'RATE']:  # Add more parameters as needed
            if param not in mod_params:
                mod_params[param] = self.interface.read(f"SOURce{channel}:MOD:{mod_type}:{param}?")
            self.interface.write(f"SOURce{channel}:MOD:{mod_type}:{param} {mod_params[param]}")

    def set_burst_mode(self, channel: int, burst_params: dict):
        """
        Sets the device to burst mode with the specified parameters.

        Args:
            channel (int): The output channel to set.
            burst_params (dict): Dictionary of parameters for burst mode.
                Expected keys are 'NCYC', 'MODE', 'TRIG', 'PHAS' etc.
        """
        self.interface.write(f"SOURce{channel}:BURSt:STATe ON")
        for param in ['NCYC', 'MODE', 'TRIG', 'PHAS']:  # Add more parameters as needed
            if param not in burst_params:
                burst_params[param] = self.interface.read(f"SOURce{channel}:BURSt:{param}?")
            self.interface.write(f"SOURce{channel}:BURSt:{param} {burst_params[param]}")

    def set_sweep_mode(self, channel: int, sweep_params: dict):
        """
        Sets the device to sweep mode with the specified parameters.

        Args:
            channel (int): The output channel to set.
            sweep_params (dict): Dictionary of parameters for sweep mode.
                Expected keys are 'STAR', 'STOP', 'TIME', 'SPAC' etc.
        """
        self.interface.write(f"SOURce{channel}:SWEEp:STATe ON")
        for param in ['STAR', 'STOP', 'TIME', 'SPAC']:  # Add more parameters as needed
            if param not in sweep_params:
                sweep_params[param] = self.interface.read(f"SOURce{channel}:SWEEp:{param}?")
            self.interface.write(f"SOURce{channel}:SWEEp:{param} {sweep_params[param]}")

    def get_mode(self, channel: int):
        """
        Gets the current mode of the device along with its parameters.

        Args:
            channel (int): The output channel to check.

        Returns:
            dict: A dictionary containing the current mode and its parameters.
        """
        sweep_state = self.interface.read(f"SOURce{channel}:SWEEp:STATe?")
        burst_state = self.interface.read(f"SOURce{channel}:BURSt:STATe?")
        mod_state = self.interface.read(f"SOURce{channel}:MOD:STATe?")
        mod_type = self.interface.read(f"SOURce{channel}:MOD:TYPE?") if mod_state == '1' else None

        mode_params = {}
        if sweep_state == '1':
            mode = 'sweep'
            for param in ['STAR', 'STOP', 'TIME', 'SPAC']:  # Add more parameters as needed
                mode_params[param] = self.interface.read(f"SOURce{channel}:SWEEp:{param}?")
        elif burst_state == '1':
            mode = 'burst'
            for param in ['NCYC', 'MODE', 'TRIG', 'PHAS']:  # Add more parameters as needed
                mode_params[param] = self.interface.read(f"SOURce{channel}:BURSt:{param}?")
        elif mod_state == '1':
            mode = f'mod ({mod_type})'
            for param in ['SOUR', 'DEPT', 'DEV', 'RATE']:  # Add more parameters as needed
                mode_params[param] = self.interface.read(f"SOURce{channel}:MOD:{mod_type}:{param}?")
        else:
            mode = 'off'

        return {"mode": mode, "parameters": mode_params}

    def get_status(self, channel: int) -> str:
        status = []

        status.append(f'Output: {self.get_output_status(channel)}')
        status.append(f'Current mode: {self.get_mode(channel)}')
        status.append(f'Current waveform parameters: {self.get_waveform_parameters(channel)}')

        return ', '.join(status)

    def get_output_status(self, channel: int) -> str:
        return 'ON' if self.interface.read(f"OUTPut{channel}?") == '1' else 'OFF'

    def get_waveform_parameters(self, channel: int) -> dict:
        """_summary_

        Args:
            channel (int): _description_

        Returns:
            dict: 
            'waveform_type': waveform_type,
            'frequency': frequency,
            'amplitude': amplitude,
            'offset': offset,
        """
        waveform_type = self.interface.read(f"SOURce{channel}:FUNCtion?")
        frequency = self.interface.read(f"SOURce{channel}:FREQuency:FIXed?")
        amplitude = self.interface.read(f"SOURce{channel}:VOLTage:LEVel:IMMediate:AMPLitude?")
        offset = self.interface.read(f"SOURce{channel}:VOLTage:LEVel:IMMediate:OFFSet?")

        return {
            'waveform_type': waveform_type,
            'frequency': frequency,
            'amplitude': amplitude,
            'offset': offset,
        }

    def is_connection_alive(self) -> bool:
        try:
            _ = self.interface.read(f"SOURce1:FUNCtion?")
            if _ is None:
                # this is purely to simulate when in hardware mock to disconnect the device (i.e. when sending via the API flask server simulate_kill 'kill' : 'true' (look at notebooks))
                return False
            print(f"Received identity: {_}")
            return True
        except:
            return False


class DG4202StateMachine(DG4202):

    def __init__(self):
        self.state = {
            "*STB?": "0",
            "SOURce1:SWEEp:STATe": "0",
            "SOURce1:BURSt:STATe": "0",
            "SOURce1:MOD:STATe": "0",
            "SOURce1:MOD:TYPE": "none",
            "OUTPut1": "0",
            "SOURce1:FUNCtion": "SIN",
            "SOURce1:FREQuency:FIXed": "375.0",
            "SOURce1:VOLTage:LEVel:IMMediate:AMPLitude": "3.3",
            "SOURce1:VOLTage:LEVel:IMMediate:OFFSet": "0.0",
            "SOURce1:SWEEp:STARt": "0",
            "SOURce1:SWEEp:STOP": "0",
            "SOURce1:SWEEp:TIME": "0",
            "SOURce1:SWEEp:SPAC": "0",
            "SOURce1:BURSt:NCYC": "0",
            "SOURce1:BURSt:MODE": "0",
            "SOURce1:BURSt:TRIG": "0",
            "SOURce1:BURSt:PHAS": "0",
            "SOURce1:MOD:SOUR": "0",
            "SOURce1:MOD:DEPT": "0",
            "SOURce1:MOD:DEV": "0",
            "SOURce1:MOD:RATE": "0",
            "SOURce2:SWEEp:STATe": "0",
            "SOURce2:BURSt:STATe": "0",
            "SOURce2:MOD:STATe": "0",
            "SOURce2:MOD:TYPE": "none",
            "OUTPut2": "0",
            "SOURce2:FUNCtion": "SIN",
            "SOURce2:FREQuency:FIXed": "375.0",
            "SOURce2:VOLTage:LEVel:IMMediate:AMPLitude": "3.3",
            "SOURce2:VOLTage:LEVel:IMMediate:OFFSet": "0.0",
            "SOURce2:SWEEp:STARt": "0",
            "SOURce2:SWEEp:STOP": "0",
            "SOURce2:SWEEp:TIME": "0",
            "SOURce2:SWEEp:SPAC": "0",
            "SOURce2:BURSt:NCYC": "0",
            "SOURce2:BURSt:MODE": "0",
            "SOURce2:BURSt:TRIG": "0",
            "SOURce2:BURSt:PHAS": "0",
            "SOURce2:MOD:SOUR": "0",
            "SOURce2:MOD:DEPT": "0",
            "SOURce2:MOD:DEV": "0",
            "SOURce2:MOD:RATE": "0",
        }

    def write(self, command: str) -> None:
        if command in [
                "OUTPut1 ON", "SOURce1:SWEEp:STATe ON", "SOURce1:BURSt:STATe ON",
                "SOURce1:MOD:STATe ON", "OUTPut2 ON", "SOURce2:SWEEp:STATe ON",
                "SOURce2:BURSt:STATe ON", "SOURce2:MOD:STATe ON"
        ]:
            command, value = command.split()
            self.state[command] = '1'
        elif command in [
                "OUTPut1 OFF", "SOURce1:SWEEp:STATe OFF", "SOURce1:BURSt:STATe OFF",
                "SOURce1:MOD:STATe OFF", "OUTPut2 OFF", "SOURce1:SWEEp:STATe OFF",
                "SOURce2:BURSt:STATe OFF", "SOURce2:MOD:STATe OFF"
        ]:
            command, value = command.split()
            self.state[command] = '0'
        else:
            command, value = command.split()
            self.state[command] = value

    def read(self, command: str) -> str:
        if command.endswith("?"):
            command = command[:-1]
        return self.state.get(command, "").split(" ")[-1]


class DG4202MockInterface(DG4202Interface):

    def __init__(self, dg4202: DG4202StateMachine = None):
        self.killed = False
        if dg4202 is None:
            self.dg4202 = DG4202StateMachine()
        else:
            self.dg4202 = dg4202

    def write(self, command: str) -> None:
        if self.killed:
            return None
        self.dg4202.write(command)

    def read(self, command: str) -> str:
        if self.killed:
            return None
        return self.dg4202.read(command)

    def simulate_kill(self, kill: bool) -> None:
        self.killed = kill


class DG4202APIServer:

    def __init__(self, dg4202_interface: DG4202Interface, server_port: int = 5000) -> None:
        """
        Create a new DG4202API instance.

        Args:
            dg4202_interface (DG4202MockInterface): A DG4202Interface instance.
            server_port (int): Default port is 5000.
        """
        self.dg4202_interface = dg4202_interface
        self.app = Flask(__name__)
        self.server_port = server_port
        self.server_thread = None
        self.setup_routes()

    def setup_routes(self) -> None:
        """
        Setup Flask routes for the API.
        """

        @self.app.route('/api/command', methods=['POST'])
        def send_command() -> Union[Response, Tuple[Response, int]]:
            """
            Flask route for sending a command to the DG4202.

            Returns:
                Response: a Flask response.
            """
            command = request.json.get('command')
            if command is None:
                return jsonify({'error': f'{command} failed.'}), 400
            self.dg4202_interface.write(command)
            return jsonify({'status': f'{command} sent'}), 200

        @self.app.route('/api/simulate_kill', methods=['POST'])
        def simulate_kill() -> Union[Response, Tuple[Response, int]]:
            """
            Flask route for sending a command to the DG4202.

            Returns:
                Response: a Flask response.
            """
            if isinstance(self.dg4202_interface, DG4202MockInterface):
                kill = request.json.get('kill')
                if kill is not None:
                    if kill == 'true':
                        self.dg4202_interface.simulate_kill(True)
                        return jsonify({'status': f'{kill} sent'}), 200
                    elif kill == 'false':
                        self.dg4202_interface.simulate_kill(False)
                        return jsonify({'status': f'{kill} sent'}), 200
                return jsonify({'error': f'{kill} failed.'}), 400
            else:
                return jsonify({'error': 'interface is not a hardware mock'}), 400

        @self.app.route('/api/state', methods=['GET'])
        def get_state() -> Response:
            """
            Flask route for retrieving the state of the DG4202.

            Returns:
                Response: a Flask response.
            """
            state = request.args.get('state')
            if state is None:
                return jsonify({'error': 'state parameter is missing.'}), 422

            # Assuming self.dg4202_interface.read() accepts the state parameter
            state_value = self.dg4202_interface.read(state)

            return jsonify({'state': state_value}), 200

        @self.app.route('/api/stop', methods=['POST'])
        def stop_server():
            """
            Flask route to stop the server.
            """
            os.kill(os.getpid(), signal.SIGINT)
            return jsonify({'status': 'Server shutting down...'}), 200

    def run(self, port: int = None) -> None:
        """
        Start the Flask application in a new thread.

        Args:
            port (int, optional): The port number to listen on. Defaults to 5000.
        """
        self.server_thread = Thread(target=self._run, args=(port,))
        self.server_thread.start()

    def _run(self, port: int) -> None:
        """
        Start the Flask application.

        Args:
            port (int): The port number to listen on.
        """
        if port is None:
            self.app.run(port=self.server_port)
        else:
            self.app.run(port=port)