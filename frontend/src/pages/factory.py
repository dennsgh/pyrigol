from device.dg4202 import DG4202, DG4202Detector, DG4202MockInterface, DG4202StateMachine

DG4202_FSM = DG4202StateMachine()
DG4202_MOCK_INTERFACE = DG4202MockInterface(DG4202_FSM)


def create_dg4202(args_dict: dict) -> DG4202:
    if args_dict['hardware_mock']:
        if DG4202_MOCK_INTERFACE.killed:
            # simulate dead device
            # kill it using the --api-server feature using REST API
            return None
        else:
            return DG4202(DG4202_MOCK_INTERFACE)
    else:
        return DG4202Detector().detect_device()