import pytest
import requests
import threading
from device.dg4202 import DG4202, DG4202Mock
from api.dg4202_api import DG4202APIServer

endpoint = 'http://localhost:5000/api'


@pytest.fixture(scope='module')
def api():
    dg4202 = DG4202Mock()
    api = DG4202APIServer(dg4202, 5000)
    threading.Thread(target=api.run).start()  # run Flask app in a separate thread
    yield api
    api.shutdown()


def test_turn_on_and_off(api):
    # Test turning on
    response = requests.post(f'{endpoint}/command', json={'command': 'OUTPut1 ON'})
    assert response.status_code == 200
    assert response.json()['status'] == 'OUTPut1 ON sent'

    response = requests.get(f'{endpoint}/state', params={'state': 'OUTPut1'})
    assert response.status_code == 200
    assert response.json()['state'] == '1'

    # Test turning off
    response = requests.post(f'{endpoint}/command', json={'command': 'OUTPut1 OFF'})
    assert response.status_code == 200
    assert response.json()['status'] == 'OUTPut1 OFF sent'

    response = requests.get(f'{endpoint}/state', params={'state': 'OUTPut1'})
    assert response.status_code == 200
    assert response.json()['state'] == '0'


def test_change_waveform_parameters(api):
    # Test changing frequency
    response = requests.post(f'{endpoint}/command',
                             json={'command': 'SOURce1:FREQuency:FIXed 500.0'})
    assert response.status_code == 200
    assert response.json()['status'] == 'SOURce1:FREQuency:FIXed 500.0 sent'

    response = requests.get(f'{endpoint}/state', params={'state': 'SOURce1:FREQuency:FIXed'})
    assert response.status_code == 200
    assert response.json()['state'] == '500.0'


def test_switch_modes(api):
    # Test turning on modulation

    command = 'SOURce1:MOD:STATe ON'
    response = requests.post(f'{endpoint}/command', json={'command': command})
    print(response)
    assert response.status_code == 200
    assert response.json()['status'] == f'{command} sent'

    response = requests.get(f'{endpoint}/state', params={'state': 'SOURce1:MOD:STATe'})
    assert response.status_code == 200
    assert response.json()['state'] == '1'

    # Test turning off modulation
    command = 'SOURce1:MOD:STATe OFF'
    response = requests.post(f'{endpoint}/command', json={'command': command})
    print(response)
    assert response.status_code == 200
    assert response.json()['status'] == f'{command} sent'

    response = requests.get(f'{endpoint}/state', params={'state': 'SOURce1:MOD:STATe'})
    assert response.status_code == 200
    assert response.json()['state'] == '0'
