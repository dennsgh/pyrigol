from pages import home, dashboard, dev
import threading
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from pages import factory
from api.dg4202_api import DG4202APIServer
import argparse
import waitress
from callbacks import main_callbacks
from werkzeug.serving import make_server
import sys
from features.state_managers import DG4202Manager, StateManager, DG4202APIManager
from features.scheduler import Scheduler
# At the top of the script:


def init_managers(args_dict: dict):
    factory.state_manager = StateManager()
    factory.dg4202_manager = DG4202Manager(factory.state_manager, args_dict=args_dict)
    factory.DG4202SCHEDULER: Scheduler(function_map=factory.dg4202_manager.function_map,
                                       interval=0.001)
    factory.state_manager.write_state({'last_known_device_uptime': None})
    if args_dict.get("api_server"):
        factory.api_manager = DG4202APIManager(dg4202_manager=factory.dg4202_manager,
                                               args_dict=args_dict)
        factory.api_manager.start()


def create_app(args_dict: dict):
    app = dash.Dash(__name__,
                    external_stylesheets=[dbc.themes.BOOTSTRAP],
                    meta_tags=[{
                        "name": "viewport",
                        "content": "width=device-width, initial-scale=1"
                    }],
                    suppress_callback_exceptions=False)
    init_managers(args_dict=args_dict)
    # Generate pages
    pages = {
        "Home": home.HomePage(app=app, args_dict=args_dict),
        "DG4202": dashboard.DashboardPage(app=app, args_dict=args_dict),
        "Dev": dev.DevPage(app=app, args_dict=args_dict),
    }
    app.title = "pyrigol"

    app.scripts.config.serve_locally = True
    # Fresh start

    sidebar_header = dbc.Row([
        dbc.Col(html.H2("pyrigol", className="display-4")),
        dbc.Col(
            html.Button(
                # use the Bootstrap navbar-toggler classes to style the toggle
                html.Span(className="navbar-toggler-icon"),
                className="navbar-toggler",
                # the navbar-toggler classes don't set color, so we do it here
                style={
                    "color": "rgba(0,0,0,.5)",
                    "border-color": "rgba(0,0,0,.1)",
                },
                id="toggle",
            ),
            # the column containing the toggle will be only as wide as the
            # toggle, resulting in the toggle being right aligned
            width="auto",
            # vertically align the toggle in the center
            align="center",
        ),
        html.Div(id="sidebar-content")
    ])

    sidebar = html.Div(
        [
            sidebar_header,
            html.Div(
                [
                    html.Hr(),
                    html.P(
                        "Tools",
                        className="lead",
                    ),
                ],
                id="blurb",
            ),
            dbc.Collapse(
                dbc.Nav(
                    [
                        dbc.NavLink("Home", href="/", active="exact"),
                        dbc.NavLink("DG4202", href="/dg4202", active="exact"),
                    ],
                    vertical=True,
                    pills=True,
                ),
                id="collapse",
            ),
            dbc.Collapse(dbc.Button()),
            html.Div(id="app-uptime"),
            html.Div(id="device-uptime"),
            html.Div(id="device-status-indicator"),
        ],
        id="sidebar",
    )

    content = html.Div(id="page-content", className="mt-4")

    app.layout = html.Div([
        dcc.Location(id="url"),
        sidebar,
        content,
        dcc.Interval(
            id='global-ticker',
            interval=1 * 1000,  # in milliseconds
            n_intervals=0)
    ])

    main_callbacks(app, args_dict, pages)

    return app


def run_flask_app(app: dash.Dash, args_dict):

    flask_server = make_server('0.0.0.0', args_dict["port"], app.server)
    flask_server.serve_forever()


def run_api_server(dg4202, server_port, stop_event):
    # Your function to start the API server
    api = DG4202APIServer(dg4202=dg4202, server_port=server_port)
    api.run()


def signal_handler(signal, frame):
    print("Exit signal detected.")
    # Perform additional error handling actions here if needed
    factory.api_manager.stop()
    sys.exit(0)


def run_application():

    stop_event = threading.Event()
    parser = argparse.ArgumentParser(description="Run the pyrigol application.")
    parser.add_argument('--hardware-mock',
                        action='store_true',
                        help="Run the app in hardware mock mode.")
    parser.add_argument('--debug',
                        action='store_true',
                        default=False,
                        help='Run the application in debug mode.')
    parser.add_argument('--api-server',
                        type=int,
                        help="Launch an api server on the specified port.")
    parser.add_argument('-p',
                        '--port',
                        type=int,
                        default=8501,
                        help="Specify the port number to run on. Defaults to 8501.")
    parser.add_argument(
        '--env',
        type=str,
        default='development',
        choices=['development', 'production'],
        help="Specify the environment to run the application in. Defaults to development.")

    args = parser.parse_args()
    args_dict = vars(args)
    print(args_dict)
    app = create_app(args_dict)
    if args_dict.get('env') == 'production':
        waitress.serve(app.server, host="0.0.0.0", port=args_dict['port'])
    else:
        print(f"Running Dash Application at http://localhost:{args_dict['port']}")
        #run_flask_app(app, args_dict)
        app.run(host='0.0.0.0', port=args_dict["port"], debug=args_dict["debug"])


# set up signal handler

if __name__ == "__main__":
    run_application()