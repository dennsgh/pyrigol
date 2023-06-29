from device.dg4202 import DG4202, DG4202Detector, DG4202MockInterface, DG4202StateMachine

dg4202_sm = DG4202StateMachine()
dg4202_mock_interface = DG4202MockInterface(dg4202_sm)


def create_dg4202(args_dict: dict) -> DG4202:
    if args_dict['hardware_mock']:
        return DG4202(dg4202_mock_interface)
    else:
        return DG4202Detector().detect_device()