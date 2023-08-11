import dash
from dash import html, Input, Output, dcc
import dash.dcc.Store as Store
import dash_bootstrap_components as dbc
import time
import threading
from abc import ABC, abstractmethod

ON_INDICATOR = dbc.Badge(" ", color="success", className="round")
OFF_INDICATOR = dbc.Badge(" ", color="danger", className="round")


class Timer:

    def __init__(self):
        self.start_time = None
        self.duration = None
        self.is_running = False
        self.thread = None

    def start(self, start_time, duration):
        self.start_time = start_time
        self.duration = duration
        self.is_running = True
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def stop(self):
        self.is_running = False
        if self.thread is not None:
            self.thread.join()

    def run(self):
        while self.is_running and time.time() - self.start_time <= self.duration:
            time.sleep(1)  # sleep for 1 second
        self.is_running = False


def create_dropdown(id: str,
                    label: str,
                    options: list,
                    label_width: int = 4,
                    dropdown_width: int = 8,
                    default_value=None) -> dbc.Row:
    """
    Create a dropdown component with label and options.

    Parameters:
        id (str): ID of the dropdown component.
        label (str): Label for the dropdown.
        options (list): List of options for the dropdown.
        label_width (int): Relative width of the label text.
        dropdown_width (int): Relative width of the dropdown.
        default_value (str, optional): Default selected value. Defaults to None.

    Returns:
        dbc.Row: A row containing the label and dropdown components.
    """
    return dbc.Row([
        dbc.Col(dbc.Label(label, html_for=id, className='text-center'), width=label_width),
        dbc.Col(dcc.Dropdown(
            id=id,
            options=[{
                "label": opt,
                "value": opt
            } for opt in options],
            value=default_value if default_value is not None else (options[0] if options else None),
        ),
                className='text-center',
                width=dropdown_width)
    ],
                   align='center',
                   className="my-2")


def create_input(id: str, label: str, placeholder: str, default_value=None) -> dbc.Row:
    """
    Create an input component with label and placeholder.

    Parameters:
        id (str): ID of the input component.
        label (str): Label for the input.
        placeholder (str): Placeholder text for the input.
        default_value (str, optional): Default value for the input. Defaults to None.

    Returns:
        dbc.Row: A row containing the label and input components.
    """
    return dbc.Row([
        dbc.Col(dbc.Label(label, html_for=id), md=4),
        dbc.Col(dcc.Input(id=id, type="text", placeholder=placeholder, value=default_value), md=8)
    ],
                   className="my-2")


def create_button(id: str, label: str, default_value=None) -> dbc.Button:
    """
    Create a button component.

    Parameters:
        id (str): ID of the button component.
        label (str): Label for the button.

    Returns:
        dbc.Button: The button component.
    """
    return dbc.Button(label, id=id, color="primary", className="m-2")


class BasePage(ABC):

    def __init__(self, app: dash.Dash, args_dict: dict):
        self.app = app
        self.args_dict = args_dict
        # Create layout
        self.page_layout = self.layout()
        # Create page callbacks
        self.register_callbacks()

    @abstractmethod
    def layout(self):
        """Return the layout for the page. Should be implemented in subclasses."""
        NotImplementedError("Page layout not implemented!")

    def update_layout(self, new_layout):
        """Update the layout of the page."""
        self.page_layout = new_layout

    @abstractmethod
    def register_callbacks(self):
        """Register callbacks for the page. Should be implemented in subclasses."""
        pass


class ParameterException(Exception):
    pass
