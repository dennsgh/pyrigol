import pytest
from device.dg4202 import DG4202, DG4202Mock
from unittest.mock import Mock, patch, call

modes = ["sweep", "burst", "mod"]  # You can add more modes here if needed.
mode_command_mapping = {"sweep": "SWEEp:STATe", "burst": "BURSt:STATe", "mod": "MOD:STATe"}


@pytest.mark.parametrize("channel", [1, 2])
@pytest.mark.parametrize("mode", modes)
def test_set_mode_for_each_channel_and_mode(channel, mode):
    mock_device = DG4202Mock()
    mock_device.set_mode(channel=channel, mode=mode)
    assert mock_device.interface.state[f"SOURce{channel}:{mode_command_mapping[mode]}"] == "1"


@pytest.mark.parametrize("channel", [1, 2])
def test_get_waveform_parameters_for_each_channel(channel):
    mock_device = DG4202Mock()
    params = mock_device.get_waveform_parameters(channel=channel)
    waveform_type = params["waveform_type"]
    frequency = params["frequency"]
    amplitude = params["amplitude"]
    offset = params["offset"]
    assert waveform_type == "SIN"
    assert frequency == float(375.)
    assert amplitude == float(3.3)
    assert offset == float(0.0)


@pytest.mark.parametrize("channel", [1, 2])
def test_turn_off_modes_for_each_channel(channel):
    mock_device = DG4202Mock()
    mock_device.turn_off_modes(channel=channel)
    for mode_command in mode_command_mapping.values():
        print(mode_command)
        assert mock_device.interface.state[f"SOURce{channel}:{mode_command}"] == "0"


waveforms = DG4202.available_waveforms()


@pytest.mark.parametrize("channel", [1, 2])
@pytest.mark.parametrize("waveform", waveforms)
def test_set_waveform_for_each_channel(channel, waveform):
    mock_device = DG4202Mock()
    mock_device.set_waveform(channel=channel, waveform_type=waveform)
    assert mock_device.interface.state[f"SOURce{channel}:FUNCtion"] == waveform
