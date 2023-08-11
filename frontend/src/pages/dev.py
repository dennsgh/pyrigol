from pages.templates import BasePage

from pathlib import Path
import plotly.graph_objs as go
import pandas as pd
from dash import dcc
from dash import html


class DevPage(BasePage):

    def layout(self) -> html.Div:
        markdown = """
        Currently under development, check in later!
        """
        main_layout = html.Div([
            html.H1("Welcome"),
            dcc.Markdown(children=markdown),
        ])
        return main_layout

    def register_callbacks(self):
        return super().register_callbacks()