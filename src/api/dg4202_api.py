from device.dg4202 import DG4202Interface, DG4202MockInterface, DG4202
from flask import Flask, request, jsonify
from flask.wrappers import Response
from typing import Optional, Union, List, Tuple
from werkzeug.serving import make_server
from threading import Thread


class DG4202APIServer:

    def __init__(self, dg4202_interface: DG4202Interface, server_port: int = 5000) -> None:
        """
        Create a new DG4202API instance.

        Args:
            dg4202 (DG4202): A DG4202 instance.
            server_port (int): Default port is 5000.
        """
        self.dg4202_interface = dg4202_interface
        self.http_server = None
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
            if isinstance(self.dg4202_interface, DG4202MockInterface):
                if self.dg4202_interface.killed:
                    return jsonify({'error': f'{command} failed.'}), 400

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
            if isinstance(self.dg4202_interface, DG4202MockInterface):
                if self.dg4202_interface.killed:
                    return jsonify({'error': f'{state} failed.'}), 400

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
            self.stop()
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
            port = self.server_port

        self.http_server = make_server('0.0.0.0', port, self.app)
        self.http_server.serve_forever()
