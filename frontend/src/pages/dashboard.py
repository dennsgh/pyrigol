from pages.templates import BasePage
from pages.templates import create_dropdown, create_input, create_button
import dash_bootstrap_components as dbc
import dash
import functools
import time
from dash.dependencies import Input, Output, State
from dash import dcc, html
from pages import factory
from device.dg4202 import DG4202
from pages import factory, plotter
from datetime import datetime
from dash.exceptions import PreventUpdate

NOT_FOUND_STRING = 'Device not found!'
TIMER_INTERVAL = 1000.  # in ms
TIMER_INTERVAL_S = TIMER_INTERVAL / 1000.  # in ms

DEFAULT_TAB_STYLE = {'height': '30px', 'padding': '2px'}


class DashboardPage(BasePage):
    ticker = dcc.Interval(
        id='interval-component',
        interval=1 * 100,  # in milliseconds, e.g. every 5 seconds
        n_intervals=0)
    channel_count = 2
    link_channel = False
    # This dictionary will indirectly control the content based on mode
    all_parameters = {}
    transition = False
    error_layout = html.Div([
        dbc.Col([
            html.H1("Connection Error"),
            html.H2("", id='connect-fail-dummy'),
            ticker,
            create_button(id=f"connect-rigol", label=f"Detect"),
        ])
    ],
                            id='error-layout')
    content = []

    def __init__(self, *args, **kwargs):
        # might be unnecessary
        super().__init__(*args, **kwargs)

    def check_connection(self) -> bool:

        if self.my_generator is not None:
            is_alive = self.my_generator.is_connection_alive()
            if not is_alive:
                self.my_generator = None
            return is_alive
        return False

    def get_all_parameters(self) -> bool:
        """
        Get all parameters for each channel from the waveform generator.

        Returns:
            bool: True if parameters are successfully retrieved, False otherwise.
        """
        if self.check_connection():
            for channel in range(1, self.channel_count + 1):
                self.all_parameters[f"{channel}"] = {
                    "waveform": self.my_generator.get_waveform_parameters(channel),
                    "mode": self.my_generator.get_mode(channel),
                    "output_status": self.my_generator.get_output_status(channel)
                }
            self.all_parameters["connected"] = True
            return True
        else:
            self.my_generator = None
            for channel in range(1, self.channel_count + 1):
                self.all_parameters[f"{channel}"] = {
                    "waveform": {
                        "waveform_type": "SIN",
                        "frequency": 0.,
                        "amplitude": 0.,
                        "offset": 0.,
                    },
                    "mode": {
                        "mode": "error",
                        "parameters": {}
                    },
                    "output_status": "OFF"
                }
            self.all_parameters["connected"] = False
            return False

    def layout(self) -> html.Div:
        # run this onetime to generate the layout
        # Initialize variables
        self.my_generator = factory.create_dg4202(self.args_dict)
        self.tab_children = {}
        self.channel_layouts = {}  # The static layouts (contains layout variables)
        self.content = []  # layout shown on page
        is_connected = self.get_all_parameters()

        self.content.append(html.Div(id="dynamic-controls"))
        self.content.append(self.ticker)
        # generate for each channel
        for channel in range(1, self.channel_count + 1):
            self.channel_layouts[f"{channel}"] = {
                "off": self.generate_waveform_control(channel),
                "sweep": self.generate_sweep_control(channel),
            }

        self.tab_children = {
            "default": [
                html.Div([
                    html.Div(id=f"debug-default-{channel}"),
                    self.channel_layouts[str(channel)]["off"]
                ],
                         id=f"channel-default-{channel}")
                for channel in range(1, self.channel_count + 1)
            ],
            "sweep": [
                html.Div([
                    html.Div(id=f"debug-sweep-{channel}"),
                    self.channel_layouts[str(channel)]["sweep"]
                ],
                         id=f"channel-sweep-{channel}")
                for channel in range(1, self.channel_count + 1)
            ],
            "Settings": [
                html.Div([
                    html.Div(id=f"debug-sweep-{channel}"),
                    self.channel_layouts[str(channel)]["sweep"]
                ],
                         id=f"channel-sweep-{channel}")
                for channel in range(1, self.channel_count + 1)
            ]
        }
        self.content.append(
            dbc.Row([
                dcc.Tabs(
                    id=f"mode-tabs-{channel}",
                    value='off',
                    children=[
                        dcc.Tab(label='Default', value='off',
                                children=self.tab_children["default"]),
                        dcc.Tab(label='Sweep', value='sweep', children=self.tab_children["sweep"]),
                    ],
                )
            ]))

        self.final_layout = html.Div(
            dbc.Container([
                dbc.Row([
                    html.H1("Dashlab", className="my-4"),
                    html.H4("", id='connection-status', className="my-4")
                ])
            ] + self.content,
                          fluid=True),
            className="main-layout",  # add this to enable greying out
        )

        return self.final_layout

    def generate_sweep_control(self, channel: int) -> dbc.Col:
        """
        Generate the control components for the sweep mode.

        Parameters:
            channel (int): The channel number.

        Returns:
            dbc.Col: The column containing the sweep control components.
        """
        return dbc.Col([
            create_input(id=f"sweep-duration-{channel}",
                         label="Duration (s)",
                         placeholder=f"Sweep duration frequency CH{channel}"),
            create_input(id=f"sweep-return-{channel}",
                         label="Return (ms)",
                         placeholder=f"Sweep return time CH{channel}"),
            create_input(id=f"sweep-start-{channel}",
                         label="Start (Hz)",
                         placeholder=f"Sweep start frequency CH{channel}"),
            create_input(id=f"sweep-stop-{channel}",
                         label="Stop (Hz)",
                         placeholder=f"Sweep stop frequency CH{channel}"),
            create_button(id=f"sweep-{channel}", label=f"Sweep CH{channel}"),
        ])

    def generate_waveform_control(self, channel: int) -> dbc.Row:
        """
        Generate the control components for the waveform mode.

        Parameters:
            channel (int): The channel number.

        Returns:
            dbc.Row: The row containing the waveform control components.
        """
        waveform_plot = dcc.Graph(
            id=f"waveform-plot-{channel}",
            figure=plotter.plot_waveform(params=self.all_parameters[f"{channel}"]["waveform"]))
        channel_row = dbc.Row(  # A Row that will hold two Columns
            [
                dbc.Col(  # First Column
                    [
                        create_dropdown(id=f"waveform-type-{channel}",
                                        label=f"Waveform Type CH{channel}",
                                        options=DG4202.available_waveforms(),
                                        label_width=4,
                                        dropdown_width=4),
                        create_input(id=f"waveform-frequency-{channel}",
                                     label="Frequency(Hz)",
                                     placeholder="Frequency (Hz)",
                                     default_value=self.all_parameters[f"{channel}"]["waveform"]
                                     ["frequency"]),
                        create_input(id=f"waveform-amplitude-{channel}",
                                     label="Amplitude (V)",
                                     placeholder="Amplitude (V)",
                                     default_value=self.all_parameters[f"{channel}"]["waveform"]
                                     ["amplitude"]),
                        create_input(
                            id=f"waveform-offset-{channel}",
                            label="Offset (V)",
                            placeholder="Offset (V)",
                            default_value=self.all_parameters[f"{channel}"]["waveform"]["offset"]),
                        dbc.Row(
                            [
                                dbc.Col(create_button(id=f"set-waveform-{channel}",
                                                      label=f"Set Waveform CH{channel}"),
                                        md=4),
                                dbc.Col(create_button(id=f"output-on-{channel}",
                                                      label=f"Output ON CH{channel}"),
                                        md=4),
                                dbc.Col(create_button(id=f"output-off-{channel}",
                                                      label=f"Output OFF CH{channel}"),
                                        md=4),
                            ],
                            className="my-2",
                        ),
                    ],
                    md=6  # Set column width to 6 out of 12
                ),
                dbc.Col(  # Second Column
                    [waveform_plot],
                    md=6  # Set column width to 6 out of 12
                )
            ])

        return channel_row

    def reconnect(self):
        self.my_generator = factory.create_dg4202(self.args_dict)
        print("Reconnecting...")
        return self.check_connection()

    def register_callbacks(self):

        def update_status_on_click(channel: int, n_clicks: int):
            """
            Update the status when the output on button is clicked.

            Parameters:
                channel (int): The channel number.
                n_clicks (int): The number of clicks.

            Returns:
                str: The updated status string.
            """
            if n_clicks:
                self.my_generator.output_on_off(channel, True)
                return f"Output turned on. Current device status: {self.my_generator.get_status(channel)}"
            return dash.no_update

        def update_status_off_click(channel: int, n_clicks: int):
            """
            Update the status when the output off button is clicked.

            Parameters:
                channel (int): The channel number.
                n_clicks (int): The number of clicks.

            Returns:
                str: The updated status string.
            """
            if n_clicks:
                self.my_generator.output_on_off(channel, False)
                return f"Output turned off. Current device status: {self.my_generator.get_status(channel)}"
            return dash.no_update

        def update_waveform(channel: int, set_waveform_clicks: int, waveform_type: str,
                            frequency: str, amplitude: str, offset: str):
            """
            Update the waveform parameters and plot.

            Parameters:
                channel (int): The channel number.
                set_waveform_clicks (int): The number of clicks on the set waveform button.
                waveform_type (str): The selected waveform type.
                frequency (str): The selected frequency.
                amplitude (str): The selected amplitude.
                offset (str): The selected offset.

            Returns:
                tuple: A tuple containing the status string and the waveform plot figure.
            """
            status_string = f"{channel}"
            if self.get_all_parameters():
                print("UPDATE_WAVEFORM")
                frequency = float(frequency) if frequency else float(
                    self.all_parameters[f"{channel}"]["waveform"]["frequency"])
                amplitude = float(amplitude) if amplitude else float(
                    self.all_parameters[f"{channel}"]["waveform"]["amplitude"])
                offset = float(offset) if offset else float(
                    self.all_parameters[f"{channel}"]["waveform"]["offset"])
                waveform_type = str(waveform_type) if waveform_type else str(
                    self.all_parameters[f"{channel}"]["waveform"]["waveform_type"])

                # If a parameter is not set, pass the current value
                self.my_generator.set_waveform(channel, waveform_type, frequency, amplitude, offset)
                status_string = f"Waveform updated. Current device status: {self.my_generator.get_status(channel)}"

                figure = plotter.plot_waveform(waveform_type, frequency, amplitude, offset)

                return status_string, figure
            else:
                return NOT_FOUND_STRING, dash.no_update

        # calls the individual functionality
        def update_channel(channel: int, n_clicks_waveform: int, n_clicks_on: int,
                           n_clicks_off: int, waveform_type: str, waveform_freq: str,
                           waveform_ampl: str, waveform_off: str):
            """
            Update the channel content based on user interactions.

            Parameters:
                channel (int): The channel number.
                n_clicks_waveform (int): The number of clicks on the set waveform button.
                n_clicks_on (int): The number of clicks on the output on button.
                n_clicks_off (int): The number of clicks on the output off button.
                waveform_type (str): The selected waveform type.
                waveform_freq (str): The selected waveform frequency.
                waveform_ampl (str): The selected waveform amplitude.
                waveform_off (str): The selected waveform offset.

            Returns:
                tuple: A tuple containing the updated status string and waveform plot figure.
            """
            if self.get_all_parameters():
                ctx = dash.callback_context
                if not ctx.triggered:
                    return dash.no_update, dash.no_update
                else:
                    input_id = ctx.triggered[0]["prop_id"].split(".")[0]
                    if input_id == f"set-waveform-{channel}":
                        return update_waveform(channel, n_clicks_waveform, waveform_type,
                                               waveform_freq, waveform_ampl, waveform_off)
                    elif input_id == f"output-on-{channel}":
                        return update_status_on_click(channel, n_clicks_on), dash.no_update
                    elif input_id == f"output-off-{channel}":
                        return update_status_off_click(channel, n_clicks_off), dash.no_update
            else:
                return NOT_FOUND_STRING, dash.no_update

        for channel in range(1, self.channel_count + 1):  # Assuming we have two channels
            self.app.callback(
                Output(f"debug-default-{channel}", "children"),
                Output(f"waveform-plot-{channel}", "figure"),
                Input(f"set-waveform-{channel}", "n_clicks"),
                Input(f"output-on-{channel}", "n_clicks"),
                Input(f"output-off-{channel}", "n_clicks"),
                State(f"waveform-type-{channel}", "value"),
                State(f"waveform-frequency-{channel}", "value"),
                State(f"waveform-amplitude-{channel}", "value"),
                State(f"waveform-offset-{channel}", "value"),
            )(functools.partial(update_channel, channel))
        # Callback
        @self.app.callback(Output('connection-status', 'children'),
                           Input('global-ticker', 'n_intervals'))
        def global_ticker(n):
            if self.get_all_parameters():
                return ["Device Connected"]
            else:
                return ["Device Disconnected"]

        @self.app.callback(
            Output("connect-fail-dummy", "children"),
            Input("connect-rigol", "n_clicks"),
        )
        def reconnect(connect_n_clicks: int):
            """
            Reconnect to the device when the connect button is clicked.

            Parameters:
                connect_n_clicks (int): The number of clicks on the connect button.

            Returns:
                list: A list containing the connection status message.
            """

            if self.reconnect():
                print("Reconnected.")
                # do not modify page_layout directly
                return ["Device found. Please refresh the page."]
            else:
                return [f"Check the connection. [{datetime.now().isoformat()}]"]
                # Callback for link channels button

        @self.app.callback(Output("link-channel-state", "children"),
                           [Input("link-channels-button", "n_clicks")])
        def on_link_channels_button_click(n):
            # Toggle the link channel state each time the button is clicked
            if n is None:
                # This is the initial call, so return the default state
                return "false"
            else:
                return "true" if n % 2 != 0 else "false"
