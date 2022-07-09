from dash import html, dcc
import pandas as pd
from .styles import highlight_styles, container_styles
from datetime import timedelta
import dash_bootstrap_components as dbc

class LayoutGenerator():

    def __init__(self, df: pd.DataFrame) -> None:

        self.df = df

        latest_year = df["last_modified"].max().year
        latest_month = df["last_modified"].max().month
        latest_day = df["last_modified"].max().day
        self.latest_interaction_day = "{}-{}-{}".format(latest_year, latest_month, latest_day)
        self.num_interactions_latest_day = len(
            df[df["last_modified"] >= self.latest_interaction_day]
        )

        # average latency
        # filter empty timedeltas from dataframe
        latency_df = df[df["latency"] != timedelta()]
        self.average_latency = latency_df["latency"].sum() / latency_df["conversation_length"].sum()

        # average CSAT
        # csat_df = df[df['Rating'] > 0]
        # self.average_csat = csat_df['Rating'].mean()
        # self.headless_csat = csat_df['Rating'][csat_df['headless'] == "Headless"].mean()
        # self.screen_csat = csat_df['Rating'][csat_df['headless'] != "Headless"].mean()

    def generate_layout(self) -> html.Div:

        """
        Generate the layout/homepage of the dashboard
        """

        app_layout = html.Div(
            children=[
                html.H1(children="OAT Dashboard"),
                html.P(children="Greatest of all time :)"),
                html.Div(
                    children=[
                        html.H2("Highlights"),
                        html.Div(
                            children=[
                                html.Div(
                                    children=[
                                        html.Strong("Latest Interaction Day & Count:"),
                                        html.P(
                                            "{} / {} interaction(s)".format(
                                                self.latest_interaction_day,
                                                self.num_interactions_latest_day,
                                            )
                                        ),
                                    ],
                                    style=highlight_styles,
                                ),
                                # html.Div(
                                #     children=[html.Strong("Average CSAT:"),
                                #                 html.P(
                                #                     f"{round(self.average_csat, 2)}" \
                                #                         f" (Headless: {round(self.headless_csat,2)} /"\
                                #                             f" Screen: {round(self.screen_csat,2)})"
                                #                 )
                                #             ],
                                #     style=highlight_styles,
                                # ),
                                html.Div(
                                    children=[
                                        html.Strong("Total Conversations:"),
                                        html.P("{}".format(len(self.df))),
                                    ],
                                    style=highlight_styles,
                                ),
                                html.Div(
                                    children=[
                                        html.Strong("Average Latency:"),
                                        html.P(f"{self.average_latency.total_seconds()} seconds"),
                                    ],
                                    style=highlight_styles,
                                ),
                            ],
                            style={"display": "flex"},
                        ),
                    ]
                ),
                dbc.Modal(
                    id="search_logs_modal",
                    is_open=False,
                ),
                html.Div(
                    children=[
                        html.H2("Filter Parameters"),
                        html.Div(
                            children=[
                                dcc.Dropdown(
                                    id="filter-dropdown",
                                    style={"width": "25%", "margin": "1%"},
                                    options=[
                                        {
                                            "label": "Screen",
                                            "value": "screen",
                                        },
                                        {
                                            "label": "Headless",
                                            "value": "headless",
                                        },
                                    ],
                                    placeholder="Filter by Device type",
                                    value="",
                                ),
                                html.Div(
                                    dcc.DatePickerRange(
                                        id="date-range-filter",
                                        display_format="MMM Do, YY",
                                        start_date=self.df["last_modified"].min(),
                                        min_date_allowed=self.df["last_modified"].min()
                                        - timedelta(days=1),
                                        max_date_allowed=self.df["last_modified"].max()
                                        + timedelta(days=1),
                                        initial_visible_month=self.df[
                                            "last_modified"
                                        ].min(),
                                        end_date=self.df["last_modified"].max(),
                                    ),
                                    style={"width": "25%", "margin": "1%"},
                                ),
                                dcc.Input(
                                    id="topic-filter",
                                    type="text",
                                    style={"width": "25%", "margin": "1%"},
                                    placeholder="filter by topic",
                                ),
                                dcc.Input(
                                    id="device-id-filter",
                                    type="text",
                                    style={"width": "25%", "margin": "1%"},
                                    placeholder="filter by device id",
                                ),
                            ],
                            style={"display": "flex", "margin_botton": "5%"},
                        ),
                        # html.Div(
                        #     [
                        #         dcc.RangeSlider(
                        #             id="rating-range-filter",
                        #             min=0,
                        #             max=5,
                        #             step=0.5,
                        #             marks={
                        #                 0: "No Rating",
                        #                 1: "1 Rating",
                        #                 2: "2 Rating",
                        #                 3: "3 Rating",
                        #                 4: "4 Rating",
                        #                 5: "5 Rating",
                        #             },
                        #         ),
                        #     ],
                        #     style={"width": "75%", "margin": "auto"},
                        # ),
                    ]
                ),
                html.Div(
                    children=[
                        html.Div(
                            children=[
                                html.H2("Conversations"),
                                html.Div(style=container_styles, id="generated_conversations"),
                            ],
                            style={"width": "50%"},
                        ),
                        html.Div(
                            children=[
                                html.H2("Graphs"),
                                html.Div(
                                    children=[
                                        html.H4("How long do Conversations Last?"),
                                        dcc.Graph(id="conversation_length"),
                                        html.Br(),
                                        html.H4("How many Sessions do we have per day?"),
                                        dcc.Graph(id="session_count"),
                                        html.Br(),
                                        html.H4("What type of devices to people use?"),
                                        dcc.Graph(id="device_count"),
                                        html.Br(),
                                        html.H4(
                                            "What percentage of people do DIY vs Cooking tasks?"
                                        ),
                                        dcc.Graph(id="domain_count"),
                                        html.Br(),
                                        html.H4("Where do people drop off?"),
                                        dcc.Graph(id="phase_count"),
                                    ],
                                    style=container_styles,
                                    id="generated_graphs",
                                ),
                            ],
                            style={"width": "50%"},
                        ),
                    ],
                    style={"display": "flex", "margin": "2%"},
                ),
            ]
        )


        return app_layout