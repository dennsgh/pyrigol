from pages.templates import BasePage
from pages.templates import create_dropdown, create_input, create_button, ON_INDICATOR, OFF_INDICATOR
import dash_bootstrap_components as dbc
import dash
import functools
import time
from threading import Timer
from dash.dependencies import Input, Output, State
from dash import dcc, html
from pages import factory
from device.dg4202 import DG4202
from pages import factory, plotter
from datetime import datetime, timedelta
from dash.exceptions import PreventUpdate

from pprint import pprint

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

        self.my_generator = factory.dg4202_manager.create_dg4202()
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
                        "current_mode": "error",
                        "parameters": {
                            "off": "",
                            "sweep": {
                                "FSTART": 0,
                                "FSTOP": 0,
                                "TIME": 0,
                                "RTIME": 0,
                            },
                            "burst": "",
                            "off": "",
                        }
                    },
                    "output_status": "OFF"
                }
            self.all_parameters["connected"] = False
            return False

    def layout(self) -> html.Div:
        # run this onetime to generate the layout
        # Initialize variables
        self.link_channel = False
        self.is_scheduler_running = False
        self.is_timer_running = False

        self.my_generator = factory.dg4202_manager.create_dg4202()
        self.tab_children = {}  # Holds the layouts for each tab.
        self.channel_layouts = {}  # Holds the objects
        self.content = []  # layout shown on page
        is_connected = self.get_all_parameters()

        self.content.append(html.Div(id="dynamic-controls"))
        self.content.append(self.ticker)
        # generate for each channel
        for channel in range(1, self.channel_count + 1):
            self.channel_layouts[f"{channel}"] = {
                # off is default.
                "off": self.generate_waveform_control(channel),
                "sweep": self.generate_sweep_control(channel),
                "control": self.generate_main_controls(channel)
            }

            self.tab_children[f"{channel}"] = {
                "off": [
                    html.Div([
                        html.Div(id=f"debug-default-{channel}"),
                        self.channel_layouts[str(channel)]["off"],
                    ],
                             id=f"channel-default-{channel}",
                             style={})
                ],
                "sweep": [
                    html.Div([
                        html.Div(id=f"debug-sweep-{channel}"),
                        self.channel_layouts[str(channel)]["sweep"],
                    ],
                             id=f"channel-sweep-{channel}",
                             style={})
                ],
            }
            print(self.all_parameters[f"{channel}"]["mode"]["current_mode"])
            self.content.append(
                dbc.Row([
                    html.Div([
                        html.Div(id=f"mode-message-{channel}"),
                        dcc.Tabs(id=f"mode-tabs-{channel}",
                                 value=self.all_parameters[f"{channel}"]["mode"]["current_mode"],
                                 children=[
                                     dcc.Tab(
                                         label='Default',
                                         value='off',
                                         children=self.tab_children[f"{channel}"]["off"],
                                     ),
                                     dcc.Tab(
                                         label='Sweep',
                                         value='sweep',
                                         children=self.tab_children[f"{channel}"]["sweep"],
                                     ),
                                 ],
                                 style={}), self.channel_layouts[str(channel)]["control"]
                    ],
                             id=f"channel-wrapper-{channel}",
                             style={})
                ]))

            self.tab_children["options"] = [
                html.Div([
                    dbc.Row([
                        create_button(id="link-switch", label="Link Channels"),
                        html.Div(id="link-status")
                    ])
                ])
            ]
        self.final_layout = html.Div(
            dbc.Container([dbc.Row([
                html.H4("", id='connection-status', className="my-4"),
            ])] + self.tab_children["options"] + self.content,
                          fluid=True),
            className="main-layout",  # add this to enable greying out
        )

        return self.final_layout

    def generate_main_controls(self, channel: int) -> dbc.Row:
        timer_modal = dbc.Modal(
            [
                dbc.ModalHeader("Timer"),
                dcc.Store(id=f'timer-status-{channel}', data={'status': 'stopped'}),
                dbc.ModalBody([
                    dbc.InputGroup([
                        dbc.InputGroupText("Duration"),
                        dbc.Input(id=f"timer-duration-{channel}", type="number", min=0),
                        dbc.InputGroupText(
                            dcc.Dropdown(id=f"timer-units-{channel}",
                                         options=[{
                                             'label': 'ms',
                                             'value': 'ms'
                                         }, {
                                             'label': 's',
                                             'value': 's'
                                         }, {
                                             'label': 'm',
                                             'value': 'm'
                                         }, {
                                             'label': 'h',
                                             'value': 'h'
                                         }],
                                         value='s')),
                    ],
                                   className="mb-3"),
                    dbc.Spinner(html.Div(id=f'timer-countdown-{channel}')),
                    dcc.Interval(
                        id=f'timer-interval-{channel}',
                        interval=1000,  # in milliseconds
                        max_intervals=0  # Start paused
                    )
                ]),
                dbc.ModalFooter(
                    dbc.Button("Start Timer", id=f"timer-start-btn-{channel}", color="primary"))
            ],
            id=f"timer-modal-{channel}",
            centered=True)

        scheduler = dbc.Modal([
            dbc.ModalHeader("Scheduler"),
            dbc.ModalBody([
                dbc.InputGroup([
                    dbc.InputGroupText("Start Time"),
                    dbc.Input(id=f"scheduler-start-time-{channel}", type="time")
                ],
                               className="mb-3"),
                dbc.InputGroup([
                    dbc.InputGroupText("End Time"),
                    dbc.Input(id=f"scheduler-end-time-{channel}", type="time")
                ],
                               className="mb-3")
            ]),
            dbc.ModalFooter(dbc.Button("Set Schedule", id=f"scheduler-{channel}", color="primary"))
        ],
                              id=f"scheduler-modal-{channel}",
                              centered=True)

        return dbc.Row(
            [
                dbc.Col(
                    create_button(id=f"output-on-off-{channel}", label=f"Output CH{channel}"),
                    width={"size": "auto"},  # Set the width to "auto" for equal sizes
                ),
                dbc.Col(
                    create_button(id=f"timer-modal-open-btn-{channel}", label=f"Timer CH{channel}"),
                    width={"size": "auto"},
                ),
                dbc.Col(
                    create_button(id=f"scheduler-modal-open-btn-{channel}",
                                  label=f"Scheduler CH{channel}"),
                    width={"size": "auto"},
                ),
                dbc.Col(
                    html.Div(id=f"output-status-indicator-{channel}"),
                    width={"size": "auto"},
                ),
                timer_modal,
                scheduler
            ],
            id=f"general-control-{channel}",
            style={
                "display": "flex",
                "justify-content": "flex-start"
            },
        )

    def generate_sweep_control(self, channel: int) -> dbc.Row:
        """
        Generate the control components for the sweep mode.

        Parameters:
            channel (int): The channel number.

        Returns:
            dbc.Row: The row containing the sweep control components.
        """
        sweep_plot = dcc.Graph(
            id=f"sweep-plot-{channel}",
            figure=plotter.plot_sweep(
                params=self.all_parameters[f"{channel}"]["mode"]["parameters"]["sweep"]),
            style={
                "height": "250px",
                "width": "400px",
                "margin-left": "auto",
                "margin-right": "auto",
                "display": "block"
            }  # Adjust the height to your desired value
        )

        channel_row = dbc.Row([
            dbc.Col(
                [
                    create_input(id=f"sweep-duration-{channel}",
                                 label="Sweep (s)",
                                 placeholder=f"Sweep duration frequency CH{channel}",
                                 default_value=self.all_parameters[f"{channel}"]["mode"]
                                 ["parameters"]["sweep"]["TIME"]),
                    create_input(id=f"sweep-return-{channel}",
                                 label="Return (ms)",
                                 placeholder=f"Sweep return time CH{channel}",
                                 default_value=self.all_parameters[f"{channel}"]["mode"]
                                 ["parameters"]["sweep"]["RTIME"]),
                    create_input(id=f"sweep-start-{channel}",
                                 label="Start (Hz)",
                                 placeholder=f"Sweep start frequency CH{channel}",
                                 default_value=self.all_parameters[f"{channel}"]["mode"]
                                 ["parameters"]["sweep"]["FSTART"]),
                    create_input(id=f"sweep-stop-{channel}",
                                 label="Stop (Hz)",
                                 placeholder=f"Sweep stop frequency CH{channel}",
                                 default_value=self.all_parameters[f"{channel}"]["mode"]
                                 ["parameters"]["sweep"]["FSTOP"]),
                    dbc.Row(
                        [
                            dbc.Col(create_button(id=f"sweep-parameters-btn-{channel}",
                                                  label=f"Set Parameters CH{channel}"),
                                    md=4)
                        ],
                        className="my-2",
                    )
                ],
                md=6  # Set column width to 6 out of 12
            ),
            dbc.Col(
                [sweep_plot],
                md=6,  # Set column width to 6 out of 12
                align="center")
        ])

        return channel_row

    def generate_waveform_control(self, channel: int) -> dbc.Row:
        """
        Generate the control components for the waveform mode.

        Parameters:
            channel (int): The channel number.

        Returns:
            dbc.Row: The row containing the waveform control components.
        """

        # Timer Modal
        waveform_plot = dcc.Graph(id=f"waveform-plot-{channel}",
                                  figure=plotter.plot_waveform(
                                      params=self.all_parameters[f"{channel}"]["waveform"],),
                                  style={
                                      "height": "250px",
                                      "width": "400px",
                                      "margin-left": "auto",
                                      "margin-right": "auto",
                                      "display": "block"
                                  })  # Adjust the height to your desired value)

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
                                        md=4)
                            ],
                            className="my-2",
                        )
                    ],
                    md=6  # Set column width to 6 out of 12
                ),
                dbc.Col(  # Second Column
                    [waveform_plot],
                    md=6  # Set column width to 6 out of 12
                    ,
                    align="centered")
            ])

        return channel_row

    def reconnect(self):
        self.my_generator = factory.dg4202_manager.create_dg4202()
        print("Reconnecting...")
        return self.check_connection()

    def register_callbacks(self):

        def update_on_off_click(channel: int, n_clicks: int):
            """
            Update the status when the output on button is clicked.

            Parameters:
                channel (int): The channel number.
                n_clicks (int): The number of clicks.

            Returns:
                str: The updated status string.
            """
            # For some reason n_clicks is always None when defined like this.
            if n_clicks:
                # Toggle the main channel
                if self.get_all_parameters():
                    set_to = False if self.all_parameters[f"{channel}"][
                        "output_status"] == 'ON' else True
                    print(
                        f'{channel} is {self.all_parameters[f"{channel}"]["output_status"]} -> {set_to}'
                    )
                    self.my_generator.output_on_off(channel, set_to)
                    # on link set to the current channel's settings
                    if self.link_channel:
                        self.my_generator.output_on_off(2 if channel == 1 else 1, set_to)
                    return f"[{datetime.now().isoformat()}] Output turned {self.all_parameters[f'{channel}']['output_status']}.", dash.no_update, [
                        ON_INDICATOR if self.all_parameters[f"{channel}"]["output_status"] == 'ON'
                        else OFF_INDICATOR
                    ]

                return [f"{NOT_FOUND_STRING}"], dash.no_update, dash.no_update
            return dash.no_update, dash.no_update, dash.no_update

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

                if self.link_channel:
                    self.my_generator.set_waveform(2 if channel == 1 else 1, waveform_type,
                                                   frequency, amplitude, offset)

                status_string = f"[{datetime.now().isoformat()}] Waveform updated."

                figure = plotter.plot_waveform(waveform_type, frequency, amplitude, offset)

                return status_string, figure, dash.no_update
            else:
                return NOT_FOUND_STRING, dash.no_update, dash.no_update

        def update_sweep(channel: int, n_clicks: int, sweep: str, rtime: str, fstart: str,
                         fstop: str):
            status_string = f"{channel}"
            if n_clicks:
                if self.get_all_parameters():
                    sweep = float(sweep) if sweep else float(
                        self.all_parameters[f"{channel}"]["mode"]["parameters"]["sweep"]["TIME"])
                    rtime = float(rtime) if rtime else float(
                        self.all_parameters[f"{channel}"]["mode"]["parameters"]["sweep"]["RTIME"])
                    fstart = float(fstart) if fstart else float(
                        self.all_parameters[f"{channel}"]["mode"]["parameters"]["sweep"]["FSTART"])
                    fstop = float(fstop) if fstop else float(
                        self.all_parameters[f"{channel}"]["mode"]["parameters"]["sweep"]["FSTART"])
                    params = {"TIME": sweep, "RTIME": rtime, "FSTART": fstart, "FSTOP": fstop}
                    print(params)
                    # If a parameter is not set, pass the current value
                    self.my_generator.set_sweep_parameters(channel, params)

                    if self.link_channel:
                        self.my_generator.set_sweep_parameters(2 if channel == 1 else 1, params)

                    status_string = f"[{datetime.now().isoformat()}] Sweep parameters updated."
                    figure = plotter.plot_sweep(fstart, fstop, sweep)
                    return status_string, figure
                else:
                    return NOT_FOUND_STRING, dash.no_update
            else:
                return dash.no_update, dash.no_update

        # calls the individual functionality
        def update_channel(channel: int, n_clicks_waveform: int, n_clicks_on_off: int,
                           waveform_type: str, waveform_freq: str, waveform_ampl: str,
                           waveform_off: str):
            # Simplest way to share the same output log message.
            if self.get_all_parameters():
                ctx = dash.callback_context
                if not ctx.triggered:
                    return dash.no_update, dash.no_update, dash.no_update
                else:
                    input_id = ctx.triggered[0]["prop_id"].split(".")[0]
                    if input_id == f"set-waveform-{channel}":
                        return update_waveform(channel, n_clicks_waveform, waveform_type,
                                               waveform_freq, waveform_ampl, waveform_off)
                    elif input_id == f"output-on-off-{channel}":
                        return update_on_off_click(channel, n_clicks_on_off)
            else:
                return NOT_FOUND_STRING, dash.no_update, dash.no_update

        def toggle_timer_modal(channel, n, is_open):
            if n:
                return not is_open
            return is_open

        def toggle_scheduler_modal(channel, n, is_open):
            if n:
                return not is_open
            return is_open

        def stop_timer(channel, n, store_data):
            if n and store_data and store_data.get("status") == "started":
                store_data["status"] = "stopped"
            return store_data

        def update_mode(channel, tab: str):
            if tab:
                print(f"{channel}-{tab}")
                self.my_generator.set_mode(channel=channel, mode=tab.strip(), mod_type=None)
                self.my_generator.output_on_off(channel, False)

                if self.link_channel:
                    self.my_generator.set_mode(2 if channel == 1 else 1, mode=tab, mod_type=None)
                    self.my_generator.output_on_off(2 if channel == 1 else 1, False)
                if self.get_all_parameters():
                    return [f"Mode is {self.all_parameters[f'{channel}']['mode']['current_mode']}."]
                return ""
            else:
                return ""

        def update_scheduler_time(channel, is_open):
            if is_open:
                now = datetime.now()
                then = now + timedelta(1.0)
                return now.isoformat(), then.isoformat()
            return "", ""  # Return an empty string when the modal is closed

        def start_timer(channel, n_clicks, duration, time_unit):
            if n_clicks and duration and time_unit:
                duration = float(duration)
                if time_unit == 'm':
                    duration *= 60  # convert to seconds
                elif time_unit == 'h':
                    duration *= 3600  # convert to seconds
                elif time_unit == 'ms':
                    duration /= 1000  # convert to seconds

                # Start the interval component
                # Here you could also set max_intervals based on your timer settings
                return duration, f"Remaining time: {duration}s"
            else:
                return dash.no_update, dash.no_update

        for channel in range(1, self.channel_count + 1):
            self.app.callback(
                Output(f"debug-default-{channel}", "children"),
                Output(f"waveform-plot-{channel}", "figure"),
                Output(f"output-status-indicator-{channel}", "figure"),
                Input(f"set-waveform-{channel}", "n_clicks"),
                Input(f"output-on-off-{channel}", "n_clicks"),
                State(f"waveform-type-{channel}", "value"),
                State(f"waveform-frequency-{channel}", "value"),
                State(f"waveform-amplitude-{channel}", "value"),
                State(f"waveform-offset-{channel}", "value"),
            )(functools.partial(update_channel, channel))

            self.app.callback(
                Output(f"mode-message-{channel}", "children"),
                [Input(f"mode-tabs-{channel}", "value")],
            )(functools.partial(update_mode, channel))
            ############################## timer
            self.app.callback(
                Output(f"timer-modal-{channel}", "is_open"),
                [Input(f"timer-modal-open-btn-{channel}", "n_clicks")],
                [State(f"timer-modal-{channel}", "is_open")],
            )(functools.partial(toggle_timer_modal, channel))

            # Adjust the callback for the start_timer function:
            self.app.callback([
                Output(f'timer-interval-{channel}', 'max_intervals'),
                Output(f'timer-countdown-{channel}', 'children')
            ], [Input(f'timer-start-btn-{channel}', 'n_clicks')], [
                State(f'timer-duration-{channel}', 'value'),
                State(f'timer-units-{channel}', 'value')
            ])(functools.partial(start_timer, channel))

            self.app.callback(
                Output(f"scheduler-start-time-{channel}", "value"),
                Output(f"scheduler-end-time-{channel}", "value"),
                [Input(f"scheduler-modal-{channel}", "is_open")],
            )(functools.partial(update_scheduler_time, channel))

            self.app.callback(
                Output(f"scheduler-modal-{channel}", "is_open"),
                [Input(f"scheduler-modal-open-btn-{channel}", "n_clicks")],
                [State(f"scheduler-modal-{channel}", "is_open")],
            )(functools.partial(toggle_scheduler_modal, channel))

            self.app.callback(
                Output(f"debug-sweep-{channel}", "children"),
                Output(f"sweep-plot-{channel}", "figure"),
                Input(f"sweep-parameters-btn-{channel}", "n_clicks"),
                State(f"sweep-duration-{channel}", "value"),
                State(f"sweep-return-{channel}", "value"),
                State(f"sweep-start-{channel}", "value"),
                State(f"sweep-stop-{channel}", "value"),
            )(functools.partial(update_sweep, channel))

        @self.app.callback(Output('connection-status', 'children'),
                           Input('global-ticker', 'n_intervals'))
        def global_ticker(n):
            if self.get_all_parameters():
                return ["Device Connected"]
            else:
                return ["Device Not Found."]

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

        @self.app.callback(
            Output("link-status", "children"),
            Output("channel-wrapper-2", "style"),
            Output("link-switch", "children"),  # Add this line
            [Input("link-switch", "n_clicks")],
            [State("channel-wrapper-2", "style")])
        def toggle_link(n_clicks, channel_wrapper):
            if n_clicks:
                self.link_channel = not self.link_channel

                # Modify the styles based on the link_channel status
                if self.link_channel:
                    channel_wrapper["display"] = "none"  # Hide mode-tabs-2
                    return [""], channel_wrapper, "Unlink Channels"
                else:
                    channel_wrapper["display"] = "block"  # Show mode-tabs-2
                    return [""], channel_wrapper, "Link Channels"
            else:
                return [""], channel_wrapper, "Link Channels"  # Default return values
