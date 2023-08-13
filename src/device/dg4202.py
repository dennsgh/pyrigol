from flask import Flask, request, jsonify
import pyvisa
import abc
import re
from typing import Optional, Union, List, Tuple
from werkzeug.serving import make_server


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
        if isinstance(self.interface, DG4202MockInterface):
            self.interface.write(f"SOURce{channel}:BURSt:STATe OFF")
            self.interface.write(f"SOURce{channel}:MOD:STATe OFF")

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
                Expected keys are 'START', 'STOP', 'SWEEP'.
        """
        self.interface.write(f"SOURce{channel}:SWEEp:STATe ON")
        for param in ['START', 'STOP', 'SWEEP']:  # Add 'RETURN' if there's a corresponding command
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
        mode_params["sweep"] = self.get_sweep_parameters(channel)
        mode_params["burst"] = {}
        mode_params[f"mod ({mod_type})"] = {}
        if sweep_state == '1':
            mode = 'sweep'
        elif burst_state == '1':
            mode = 'burst'
        elif mod_state == '1':
            mode = f'mod ({mod_type})'
        else:
            mode = 'off'

        return {"current_mode": mode, "parameters": mode_params}

    def get_sweep_parameters(self, channel: int) -> dict:
        """
        Retrieves the sweep parameters currently set on the device.

        Args:
            channel (int): The output channel to check.

        Returns:
            dict: A dictionary containing the sweep parameters.
        """
        sweep_params = {}
        sweep_params['FSTART'] = float(self.interface.read(f"SOURce{channel}:FREQuency:STaRt?"))
        sweep_params['FSTOP'] = float(self.interface.read(f"SOURce{channel}:FREQuency:STOP?"))
        sweep_params['TIME'] = float(self.interface.read(f"SOURce{channel}:SWEEp:TIME?"))
        sweep_params['RTIME'] = float(self.interface.read(f"SOURce{channel}:SWEEp:RTIMe?"))
        sweep_params['HTIME_START'] = float(
            self.interface.read(f"SOURce{channel}:SWEEp:HTIMe:STaRt?"))
        sweep_params['HTIME_STOP'] = float(
            self.interface.read(f"SOURce{channel}:SWEEp:HTIMe:STOP?"))
        # Add here the command for 'RETURN' when it is known
        # sweep_params['RETURN'] = self.interface.read(f"SOURce{channel}:???")

        return sweep_params

    def set_sweep_parameters(self, channel: int, sweep_params: dict):
        """
        Sets the sweep parameters on the device.

        Args:
            channel (int): The output channel to set.
            sweep_params (dict): Dictionary of parameters for sweep mode.
        """
        if sweep_params.get('FSTART') is not None:
            self.interface.write(f"SOURce{channel}:FREQuency:STaRt {sweep_params['FSTART']}")
        if sweep_params.get('FSTOP') is not None:
            self.interface.write(f"SOURce{channel}:FREQuency:STOP {sweep_params['FSTOP']}")
        if sweep_params.get('TIME') is not None:
            self.interface.write(f"SOURce{channel}:SWEEp:TIME {sweep_params['TIME']}")
        if sweep_params.get('RTIME') is not None:
            self.interface.write(f"SOURce{channel}:SWEEp:RTIMe {sweep_params['RTIME']}")
        if sweep_params.get('HTIME_START') is not None:
            self.interface.write(f"SOURce{channel}:SWEEp:HTIMe:STaRt {sweep_params['HTIME_START']}")
        if sweep_params.get('HTIME_STOP') is not None:
            self.interface.write(f"SOURce{channel}:SWEEp:HTIMe:STOP {sweep_params['HTIME_STOP']}")

    def get_status(self, channel: int) -> str:
        status = []

        status.append(f'Output: {self.get_output_status(channel)}')
        status.append(f'Current mode: {self.get_mode(channel)}')
        status.append(f'Current waveform parameters: {self.get_waveform_parameters(channel)}')

        return ', '.join(status)

    def get_output_status(self, channel: int) -> str:
        return 'ON' if self.interface.read(f"OUTPut{channel}?").strip() in ['1', 'ON'] else 'OFF'

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
            'waveform_type': str(waveform_type),
            'frequency': float(frequency),
            'amplitude': float(amplitude),
            'offset': float(offset),
        }

    def is_connection_alive(self) -> bool:
        try:
            _ = self.interface.read(f"SOURce1:FUNCtion?")
            if _ is None:
                # this is purely to simulate when in hardware mock to disconnect the device (i.e. when sending via the API flask server simulate_kill 'kill' : 'true' (look at notebooks))
                return False
            return True
        except:
            return False


class DG4202Mock(DG4202):

    def __init__(self):
        # pass simulated interface
        self.killed = False
        super().__init__(DG4202MockInterface())

    def simulate_kill(self, kill: bool):
        self.killed = kill

    def killed_state_method(self, *args, **kwargs):
        raise Exception("Device is disconnected!")

    def is_connection_alive(self) -> bool:
        return not self.killed

    def __getattribute__(self, name):
        # Only block methods that actually perform operations
        blocked_methods = {
            "set_waveform",
            "turn_off_modes",
            "check_status",
            "output_on_off",
            "set_mode",
            "set_modulation_mode",
            "set_burst_mode",
            "set_sweep_mode",
            "get_mode",
            "get_sweep_parameters",
            "set_sweep_parameters",
            "get_status",
            "get_output_status",
            "get_waveform_parameters",
            #"is_connection_alive"
        }

        if object.__getattribute__(self, "killed") and name in blocked_methods:
            return self.killed_state_method
        else:
            return object.__getattribute__(self, name)


class DG4202MockInterface(DG4202Interface):

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
            "SOURce1:FREQuency:STOP": "0",
            "SOURce1:FREQuency:STaRt": "0",
            "SOURce1:SWEEp:STOP": "0",
            "SOURce1:SWEEp:TIME": "1.0",
            "SOURce1:SWEEp:HTIMe:STaRt": "0",
            "SOURce1:SWEEp:HTIMe:STOP": "0",
            "SOURce1:SWEEp:RTIMe": "0",
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
            "SOURce2:FREQuency:STOP": "0",
            "SOURce2:FREQuency:STaRt": "0",
            "SOURce2:SWEEp:STOP": "0",
            "SOURce2:SWEEp:TIME": "1.0",
            "SOURce2:SWEEp:HTIMe:STaRt": "0",
            "SOURce2:SWEEp:HTIMe:STOP": "0",
            "SOURce2:SWEEp:RTIMe": "0",
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
                "SOURce1:MOD:STATe OFF", "OUTPut2 OFF", "SOURce2:SWEEp:STATe OFF",
                "SOURce2:BURSt:STATe OFF", "SOURce2:MOD:STATe OFF"
        ]:
            command, value = command.split()
            self.state[command] = '0'
        else:
            command, value = command.split()
            self.state[command] = value
        print(f"setting {command} {value}")

    def read(self, command: str) -> str:
        if command.endswith("?"):
            command = command[:-1]
        return self.state.get(command, "").split(" ")[-1]


if __name__ == "__main__":
    my_generator = DG4202Detector().detect_device()
    print(my_generator.get_sweep_parameters(1))