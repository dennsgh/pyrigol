import pytest
from unittest.mock import Mock, patch
from device.dg4202 import DG4202Detector, DG4202


def test_detect_device_with_tcpip_resource():
    """
    Test if the DG4202Detector can correctly detect a DG4202 device connected via TCPIP.
    """
    # Mock the ResourceManager from pyvisa and the methods we're going to use.
    mock_rm = Mock()
    mock_device = Mock()

    # Simulate a device response which contains the identifier "DG4202".
    mock_device.query.return_value = "Some info DG4202 More info"

    # Simulate a device resource list that contains a TCPIP resource.
    mock_rm.list_resources.return_value = ["TCPIP0::192.168.1.100::INSTR"]

    # Return our mock device when trying to open the resource.
    mock_rm.open_resource.return_value = mock_device

    # Patch the pyvisa ResourceManager to use our mocked version.
    with patch('device.dg4202.pyvisa.ResourceManager', return_value=mock_rm):
        result = DG4202Detector.detect_device()

    # Ensure the result is an instance of the DG4202 class.
    assert isinstance(result, DG4202)


def test_detect_device_with_usb_resource():
    """
    Test if the DG4202Detector can correctly detect a DG4202 device connected via USB.
    """
    # Mock the ResourceManager from pyvisa and the methods we're going to use.
    mock_rm = Mock()
    mock_device = Mock()

    # Simulate a device response which contains the identifier "DG4202".
    mock_device.query.return_value = "Some info DG4202 More info"

    # Simulate a device resource list that contains a USB resource.
    mock_rm.list_resources.return_value = ["USB0::0x1234::0x5678::SN12345::0::INSTR"]

    # Return our mock device when trying to open the resource.
    mock_rm.open_resource.return_value = mock_device

    # Patch the pyvisa ResourceManager to use our mocked version.
    with patch('device.dg4202.pyvisa.ResourceManager', return_value=mock_rm):
        result = DG4202Detector.detect_device()

    # Ensure the result is an instance of the DG4202 class.
    assert isinstance(result, DG4202)


def test_detect_device_with_no_device():
    """
    Test the scenario where no DG4202 device is detected.
    """
    # Mock the ResourceManager from pyvisa.
    mock_rm = Mock()

    # Simulate an empty resource list (i.e., no devices detected).
    mock_rm.list_resources.return_value = []

    # Patch the pyvisa ResourceManager to use our mocked version.
    with patch('device.dg4202.pyvisa.ResourceManager', return_value=mock_rm):
        result = DG4202Detector.detect_device()

    # Ensure that the detection result is None when no devices are found.
    assert result is None
