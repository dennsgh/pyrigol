import dash
import functools
from dash.dependencies import Input, Output, State
from device.dg4202 import DG4202, DG4202Detector
from dash import html
import traceback
import dash_bootstrap_components as dbc
from pages import factory, plotter


def main_callbacks(app: dash.Dash, args_dict: dict, pages: dict):

    @app.callback(dash.dependencies.Output('page-content', 'children'),
                  [dash.dependencies.Input('url', 'pathname')])
    def display_page(pathname):
        try:
            print(f"{pathname}")
            if pathname == '/' or pathname == '/home':
                return pages["Home"].page_layout
            elif pathname == '/dashlab':
                return pages["Dashlab"].page_layout
            else:
                return '404 - Page not found'
        except Exception as e:
            return html.Div([
                html.H3('Error during render.'),
                html.Pre(traceback.format_exc()),
                html.P(f'{e}'),
            ])

    @app.callback(Output('app-uptime', 'children'), Output('device-uptime', 'children'),
                  Output('device-status-indicator', 'children'),
                  Input('global-ticker', 'n_intervals'))
    def update_uptime(n):
        if factory.create_dg4202(args_dict) is not None:
            indicator = [dbc.Badge(" ", color="success",
                                   className="round")]  # Green Badge for success
        else:
            indicator = [dbc.Badge(" ", color="danger", className="round")]  # Red Badge for failure

        app_uptime = [f"App Uptime : {factory.get_uptime()}"]
        device_uptime = [f"Device Uptime : {factory.get_device_uptime(args_dict)}"]

        return app_uptime, device_uptime, indicator
