import pytest
from unittest.mock import MagicMock, patch
from device.dg4202 import DG4202Detector, DG4202Ethernet, DG4202USB  # change `yourmodule` to the name of your module


@patch('pyvisa.ResourceManager')
def test_DG4202Detector_detect_device(mock_rm):
    # Mock the ResourceManager and its methods
    mock_rm.list_resources.return_value = [
        "TCPIP::192.168.1.1::INSTR", "USB0::0x1AB1::0x0641::DG4202::INSTR"
    ]
    mock_rm.open_resource.return_value.query.return_value = "*IDN? Rigol Technologies,DG4202,DG4E2123456789,00.01.09.00.02"

    # Call the method under test
    detected_device = DG4202Detector.detect_device()

    # Validate that the correct calls were made
    mock_rm.list_resources.assert_called_once()
    assert mock_rm.open_resource.call_count == 2

    # Validate the type of the detected device based on the IP/Resource
    assert isinstance(detected_device, DG4202Ethernet) or isinstance(detected_device, DG4202USB)


@patch('pyvisa.ResourceManager')
def test_DG4202Ethernet_read_write(mock_rm):
    # Mock the ResourceManager and its methods
    mock_rm.open_resource.return_value.query.return_value = "Mocked response"
    mock_rm.open_resource.return_value.write.return_value = None

    # Call the method under test
    dg4202ethernet = DG4202Ethernet('192.168.1.1')
    write_response = dg4202ethernet.write('*IDN?')
    read_response = dg4202ethernet.read('*IDN?')

    # Validate that the correct calls were made
    mock_rm.open_resource.assert_called_once_with('TCPIP::192.168.1.1::INSTR')
    assert write_response is None
    assert read_response == "Mocked response"


@patch('pyvisa.ResourceManager')
def test_DG4202USB_read_write(mock_rm):
    # Mock the ResourceManager and its methods
    mock_rm.open_resource.return_value.query.return_value = "Mocked response"
    mock_rm.open_resource.return_value.write.return_value = None

    # Call the method under test
    dg4202usb = DG4202USB('USB0::0x1AB1::0x0641::DG4202::INSTR')
    write_response = dg4202usb.write('*IDN?')
    read_response = dg4202usb.read('*IDN?')

    # Validate that the correct calls were made
    mock_rm.open_resource.assert_called_once_with('USB0::0x1AB1::0x0641::DG4202::INSTR')
    assert write_response is None
    assert read_response == "Mocked response"
