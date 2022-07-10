from typing import List, Union
from boto3.dynamodb.conditions import Key
from utils import ComposedDB
from taskmap_pb2 import Session, ConversationTurn
from searcher_pb2 import SearchLog

from dash import html, dcc, Dash, callback_context
import pandas as pd
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

import plotly.express as px

from datetime import timedelta, datetime
from dash.dependencies import Input, Output, State, ALL, MATCH
import os
from waitress import serve

from src import (
    get_session_attributes,
    read_database,
    LayoutGenerator,
    Extractor
)

# load feedback csv files as dataframes
# conversation_feedback = pd.read_csv("../user_feedback.csv")  # usually empty
# team_ratings = pd.read_csv("../user_ratings.csv")

# instantiate a dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.COSMO])

prefix = os.environ.get("DB_ENVIRONMENT", "Undefined")
database_url = os.environ.get("DATABASE_URL", None)
sessions_db = ComposedDB(
    proto_class=Session,
    url=database_url,
    prefix=prefix,
    primary_key="session_id",
    sub_proto_config={
        "turn": {
            "proto_class": ConversationTurn, 
            "primary_key": "id"
        },
    },
)

search_logs_db = ComposedDB(
    proto_class=SearchLog,
    url=database_url,
    prefix=prefix,
    primary_key="id",
    sub_proto_config={}
)

sessions_list = read_database(sessions_db)
search_logs_list = read_database(search_logs_db)
# DataFrames Init
sessions_df = pd.DataFrame.from_dict(sessions_list)
search_logs_df = pd.DataFrame.from_dict(search_logs_list)

extractor = Extractor()
if len(sessions_list) > 0:
    sessions_df = extractor.extract_session_attributes(sessions_df)

if len(search_logs_list) > 0:
    search_logs_df = extractor.extract_search_log_ids(search_logs_df)

# assign layout to app
layout_generator = LayoutGenerator(sessions_df)
app.layout = layout_generator.generate_layout()


@app.callback(
    Output("generated_conversations", "children"),
    Output("conversation_length", "figure"),
    Output("session_count", "figure"),
    Output("device_count", "figure"),
    Output("domain_count", "figure"),
    Output("phase_count", "figure"),
    Input("filter-dropdown", "value"),
    Input("date-range-filter", "start_date"),
    Input("date-range-filter", "end_date"),
    Input("topic-filter", "value"),
    Input("device-id-filter", "value"),
    # Input("rating-range-filter", "value"),
    prevent_initial_call=True,
)
def update_conversations_and_graphs(
    filter_dropdown_value,
    date_range_start,
    date_range_end,
    topic_filter_value,
    device_id_value,
    # rating_range_value,
):
    """
    Callback function to dynamically update conversations and graphs in interface
    """
    filtered_df = sessions_df

    turn_ids = search_logs_df['turn_id'].values.tolist()

    if filter_dropdown_value == "screen":
        filtered_df = sessions_df[sessions_df["headless"] == "Screen"]

    if filter_dropdown_value == "headless":
        filtered_df = sessions_df[sessions_df["headless"] == "Headless"]

    date_range_start_date = date_range_start[0:10]

    date_range_end_date = date_range_end[0:10]

    filtered_df = filtered_df[
        (filtered_df["last_modified"] >= date_range_start_date)
        & (filtered_df["last_modified"] <= date_range_end_date)
    ]

    if topic_filter_value:
        filtered_df = filtered_df[
            filtered_df["conversation_text"]
            .str.lower()
            .str.contains(topic_filter_value)
        ]

    if device_id_value:
        filtered_df = filtered_df[
            filtered_df["session_id"].str.contains(device_id_value, case=False)
        ]
    
    # if rating_range_value:
    #     filtered_df = filtered_df[
    #         (filtered_df['Rating'] >= rating_range_value[0])
    #         & (filtered_df['Rating'] <= rating_range_value[1])
    #     ]

    nested_divs = [
        get_session_attributes(session, turn_ids) for _, session in filtered_df.iterrows()
    ]

    filtered_df = filtered_df.sort_values(by="last_modified")
    conversation_length = px.line(
        filtered_df, x="last_modified", y="conversation_length"
    )
    conversation_length.update_layout(transition_duration=500)

    grouped_by_day = (
        filtered_df["last_modified"]
        .dt.floor("d")
        .value_counts()
        .rename_axis("date")
        .reset_index(name="count")
    )
    grouped_by_day = grouped_by_day.sort_values(by="date")
    session_count = px.bar(grouped_by_day, x="date", y="count")

    headless_count_df = pd.DataFrame(filtered_df["headless"].value_counts())
    headless_count_df["device_names"] = headless_count_df.index
    headless_count_fig = px.pie(
        headless_count_df, values="headless", names="device_names"
    )

    domain_count_df = pd.DataFrame(filtered_df["domain"].value_counts())
    domain_count_df["domain_names"] = domain_count_df.index
    domain_count_fig = px.pie(domain_count_df, values="domain", names="domain_names")

    phase_count_df = pd.DataFrame(filtered_df["phase"].value_counts())
    phase_count_df["phase_names"] = phase_count_df.index
    phase_count_fig = px.pie(phase_count_df, values="phase", names="phase_names")

    return (
        html.Div(nested_divs),
        conversation_length,
        session_count,
        headless_count_fig,
        domain_count_fig,
        phase_count_fig
    )


@app.callback(
    Output("search_logs_modal", "is_open"),
    Output("search_logs_modal", "children"),
    Input({'type': 'search_log', 'index': ALL, 'session_id': ALL}, 'n_clicks'),
    State("search_logs_modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_modal(n_clicks: List, is_open: bool) -> Union[bool, List]:

    """
    Callback function to toggle modal when search result utterance is clicked
    """

    # if all input n_clicks are none, then conversations were just loaded
    if not any(n_clicks):
        raise PreventUpdate

    # get the full id of the session that was clicked
    turn_id = eval(callback_context.triggered[0]['prop_id'][:-9])['index']
    session_id = eval(callback_context.triggered[0]['prop_id'][:-9])['session_id']

    # filter dataframe for the session id of the log that was clicked (there are duplicates)
    filtered_df = search_logs_df[
        (search_logs_df['session_id'] == session_id) 
        & (search_logs_df['turn_id'] == turn_id)
    ]

    modal_title = dbc.ModalHeader(dbc.ModalTitle(f"{session_id[:25]}"))
    modal_content = []
    modal_body_text = "No Search Logs!"

    if isinstance(filtered_df.iloc[0]['search_query'], dict):
        modal_body_text = f"RETRIEVED TASKMAPS \U000027A1 \n"
        # print(session["l2r_doc"])
        sorted_l2r_doc = sorted(filtered_df.iloc[0]['l2r_doc'], key=lambda item: float(item['l2r_score']), reverse=True)
        # print("-------")
        # print(sorted_l2r_doc)
        for result in sorted_l2r_doc:
            modal_body_text += f"{result['title']}: {result['l2r_score']} \U0001F50E \n"

        modal_body = dbc.ModalBody(modal_body_text)
    
        modal_footer = dbc.ModalFooter(
            [
                dbc.Button(
                    "Detailed Logs", 
                    n_clicks=0,
                    id={
                        'type': 'download_log_btn',
                        'index': turn_id,
                        'session_id': session_id
                    }
                ),
                dcc.Download(
                    id={
                        'type': 'download_log',
                        'index': turn_id,
                        'session_id': session_id
                    }
                )
            ]
        )

        modal_content.extend([modal_title, modal_body, modal_footer])
    
    else: 
        modal_body = dbc.ModalBody(modal_body_text)
        modal_content = [modal_title, modal_body]

    if n_clicks:
        return not is_open, modal_content
    return is_open, modal_content

@app.callback(
    Output({'type': 'download_log', 'index': MATCH, 'session_id': MATCH}, 'data'),
    Input({'type': 'download_log_btn', 'index': MATCH, 'session_id': MATCH}, 'n_clicks'),
    prevent_initial_call=True,
)
def download_logs(n_clicks: List):
    """
    Callback function to download logs
    """

    turn_id = eval(callback_context.triggered[0]['prop_id'][:-9])['index']
    session_id = eval(callback_context.triggered[0]['prop_id'][:-9])['session_id']

    filtered_df = search_logs_df[
        (search_logs_df['session_id'] == session_id) 
        & (search_logs_df['turn_id'] == turn_id)
    ]

    # we already know it has search logs because of prior call back implementation
    sorted_l2r_doc = sorted(filtered_df.iloc[0]['l2r_doc'], key=lambda item: float(item['l2r_score']), reverse=True)
    l2r_df = pd.DataFrame.from_dict(sorted_l2r_doc)

    return dcc.send_data_frame(l2r_df.to_csv, f"{session_id}.csv")


if __name__ == "__main__":
    # app.run_server(debug=True, port=7500, host="0.0.0.0")
    serve(app.server, port=7500, host="0.0.0.0", threads=6)
