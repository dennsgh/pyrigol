import pytest
from device.dg4202 import DG4202Detector, DG4202Ethernet, DG4202USB


@pytest.mark.hardware
def test_DG4202Detector_detect_device():
    detected_device = DG4202Detector.detect_device()

    # Check that the returned object is not None and of the correct type
    assert detected_device is not None
    assert isinstance(detected_device.interface, DG4202Ethernet) or isinstance(
        detected_device.interface, DG4202USB)


"""
@pytest.mark.hardware
def test_DG4202Ethernet_read_write():
    dg4202ethernet = DG4202Ethernet('192.168.1.1')

    # Assuming the device connected responds with a valid "*IDN?" response
    assert dg4202ethernet.read('*IDN?').startswith('*IDN? Rigol Technologies,DG4202')

    # You can't really assert the result of the write method unless it returns something


@pytest.mark.hardware
def test_DG4202USB_read_write():
    dg4202usb = DG4202USB('USB0::0x1AB1::0x0641::DG4202::INSTR')

    # Assuming the device connected responds with a valid "*IDN?" response
    assert dg4202usb.read('*IDN?').startswith('*IDN? Rigol Technologies,DG4202')

    # You can't really assert the result of the write method unless it returns something
"""