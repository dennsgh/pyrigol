import dash
from dash import html, Input, Output
import dash.dcc.Store as Store


class BasePage:

    def __init__(self, app: dash.Dash, args_dict: dict):
        self.app = app
        self.args_dict = args_dict
        # Create layout
        self.default_logic = [
            html.Div(id='dynamic-content'),
            html.Div(id='layout-update-trigger', style={'display': 'none'})
        ]
        self.page_layout = html.Div([self.layout()] + self.default_logic)
        # Create page callbacks
        # Callback that gets triggered by the trigger and updates the layout

        self.register_callbacks()

    def layout(self):
        raise NotImplementedError("You should implement the 'layout' method!")

    def update_layout(self, new_layout):
        self.page_layout = html.Div([new_layout] + self.default_logic)

    def register_callbacks(self):
        pass


class ParameterException(Exception):
    pass
