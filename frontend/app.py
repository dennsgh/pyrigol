from pages import home, dashboard
import threading
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from pages import factory
from device.dg4202 import DG4202APIServer
import argparse
import waitress
from callbacks import main_callbacks
from threading import Barrier
from werkzeug.serving import make_server


def get_sidebar_layout(current_page):
    common_sidebar_elements = [
        html.H2("Navigation"),
        dcc.Link("Home", href="/"),
        html.Br(),
        dcc.Link("Dashlab", href="/dashlab"),
        html.Br()
    ]

    if current_page == "Home":
        return html.Div(common_sidebar_elements)
    elif current_page == "Dashlab":
        return html.Div(common_sidebar_elements)
    else:
        return html.Div([])


def create_app(args_dict):
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        meta_tags=[{
            "name": "viewport",
            "content": "width=device-width, initial-scale=1"
        }],
        suppress_callback_exceptions=True  # Add this line,
    )
    # Generate pages
    pages = {
        "Home": home.HomePage(app=app, args_dict=args_dict),
        "Dashlab": dashboard.DashboardPage(app=app, args_dict=args_dict)
    }
    app.title = "pyrigol"

    app.scripts.config.serve_locally = True

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
                        dbc.NavLink("Dashlab", href="/dashlab", active="exact"),
                    ],
                    vertical=True,
                    pills=True,
                ),
                id="collapse",
            ),
            dbc.Collapse(dbc.Button())
        ],
        id="sidebar",
    )

    content = html.Div(id="page-content", className="mt-4")

    app.layout = html.Div([dcc.Location(id="url"), sidebar, content])

    main_callbacks(app, args_dict, pages)

    return app


def run_dash_application(app, args_dict):
    waitress.serve(app.server, host="0.0.0.0", port=args_dict['port'])


def run_flask_app(app, host, port):
    flask_server = make_server(host, port, app.server)
    flask_server.serve_forever()


def run_api_server(interface, server_port):
    # Your function to start the API server
    api = DG4202APIServer(dg4202_interface=interface, server_port=server_port)
    api.run()


def run_application():
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
        # Start the Flask app in one thread
        print(f"Starting Application at http://localhost:{args_dict['port']}")
        flask_thread = threading.Thread(target=run_flask_app,
                                        args=(app, '0.0.0.0', args_dict['port']))

        flask_thread.start()

        if args_dict.get("api_server"):
            print(f"Running DG4202 API server on port http://localhost:{args_dict['api_server']}.")

            # Start the API server in another thread
            if args_dict["hardware_mock"]:
                api_thread = threading.Thread(target=run_api_server,
                                              args=(factory.create_dg4202(args_dict),
                                                    args_dict['api_server']))
            else:
                api_thread = threading.Thread(target=run_api_server,
                                              args=(factory.dg4202_mock_interface,
                                                    args_dict['api_server']))
            api_thread.start()

        # Join the threads
        flask_thread.join()
        api_thread.join()


if __name__ == "__main__":
    run_application()