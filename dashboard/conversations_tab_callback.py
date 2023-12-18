import dash
import json

from utils import logger

from typing import List, Union
from dash import html, dcc, Dash, callback_context
from dash.dependencies import Input, Output, State, ALL, MATCH
from dash.exceptions import PreventUpdate

import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd

from src import (
    get_session_attributes,
)


def register_conv_callbacks(app, sessions_df, search_logs_df, team_ratings):
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
        Input("rating-range-filter", "value"),
        Input({"type": "memory", "index": ALL, "session_id": ALL}, "data"),
        prevent_initial_call=True,
    )
    def update_conversations_and_graphs(
            filter_dropdown_value,
            date_range_start,
            date_range_end,
            topic_filter_value,
            device_id_value,
            rating_range_value,
            data
    ):
        """
        Callback function to dynamically update conversations and graphs in interface
        """
        changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0].split(".")[0]
        if changed_id not in ["rating-range-filter", "device-id-filter", "topic-filter", "date-range-filter",
                              "filter-dropdown"]:
            # prevent the None callbacks to make sure we only update the conversations when any of the
            # filter buttons are selected.
            raise PreventUpdate

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

        if rating_range_value:
            filtered_df = filtered_df[
                (filtered_df['Rating'] >= rating_range_value[0])
                & (filtered_df['Rating'] <= rating_range_value[1])
                ]

        nested_divs = [
            get_session_attributes(session, turn_ids, data) for _, session in filtered_df.iterrows()
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
        try:
            grouped_by_day = grouped_by_day.sort_values(by="date")
            session_count = px.bar(grouped_by_day, x="date", y="count")

            headless_count_df = pd.DataFrame(filtered_df["headless"].value_counts())
            headless_count_df["device_names"] = headless_count_df.index
            headless_count_df.rename(columns={'headless': 'device_names', 'device_names': 'count'}, inplace=True)
            headless_count_fig = px.pie(
                headless_count_df, values="count", names="device_names"
            )
            domain_count_df = pd.DataFrame(filtered_df["domain"].value_counts())
            domain_count_df["domain_names"] = domain_count_df.index
            domain_count_df.rename(columns={'domain': 'count'}, inplace=True)
            domain_count_fig = px.pie(domain_count_df, values="count", names="domain_names")

            phase_count_df = pd.DataFrame(filtered_df["phase"].value_counts())
            phase_count_df["phase_names"] = phase_count_df.index
            phase_count_df.rename(columns={'phase': 'count'}, inplace=True)
            phase_count_fig = px.pie(phase_count_df, values="count", names="phase_names")
        except Exception as e:
            logger.info(e)
            headless_count_fig = px.pie()
            domain_count_fig = px.pie()
            phase_count_fig = px.pie()

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
        Output({"type": "download-csv", "index": MATCH, "session_id": MATCH}, "data"),
        Input({"type": "btn-download-csv", "index": MATCH, "session_id": MATCH}, "n_clicks"),
        State({"type": "btn-download-csv", "index": MATCH, "session_id": MATCH}, "id"),
        prevent_initial_call=True,
    )
    def download_full_session_for_annotation(n_clicks_list, button_ids):
        ctx = dash.callback_context
        triggered_button_info = ctx.triggered[0]["prop_id"].split(".")[0]
        session_id = json.loads(triggered_button_info)["session_id"]

        filtered_df = sessions_df[
            sessions_df["session_id"].str.contains(session_id, case=False)
        ]

        session = filtered_df.iloc[0]

        date = "{}-{}-{}".format(session["last_modified"].year, session["last_modified"].month,
                                       session["last_modified"].day)
        session_id = session["session_id"]

        rows = []

        for session_turn in session['turn']:
            turn_dict = {"date": date, "session_id": session_id, 'turn_id': session_turn['id']}
            user_interaction = session_turn["user_request"]["interaction"]
            user_text = user_interaction.get("text", "NO USER TEXT")
            turn_dict['user_request'] = user_text if user_text != "NO USER TEXT" else user_interaction.get('intents')

            system_intent_classification = session_turn["user_request"]["interaction"]
            params = system_intent_classification.get('params', "")
            turn_dict['system_intent'] = params

            agent_response = session_turn["agent_response"]["interaction"]
            bot_text = agent_response.get("speech_text", "NO SPEECH TEXT")
            turn_dict['bot_text'] = bot_text

            rows.append(turn_dict)

        df = pd.DataFrame(rows)

        logger.info(f'Downloading {session_id} to csv...')

        return dcc.send_data_frame(df.to_csv, f"{session_id}.csv")

    @app.callback(
        Output({"type": "memory", "index": MATCH, "session_id": MATCH}, "data"),
        Input({"type": "rating-slider", "index": MATCH, "session_id": MATCH}, "value"),
        State({"type": "rating-slider", "index": MATCH, "session_id": MATCH}, "id"),
        prevent_initial_call=True
    )
    def save_rating_into_session_memory(value, state):
        session_id = state["session_id"]
        logger.info(f'Rating given for {session_id}: {value}')
        return {"session_id": session_id, "our rating": value}

    @app.callback(
        Output("download-ratings", "data"),
        Input("btn-download-ratings", "n_clicks"),
        Input({"type": "memory", "index": ALL, "session_id": ALL}, "data"),
        prevent_initial_call=True,
    )
    def download_annotator_ratings(n_clicks, data):
        completed_ratings = []
        for row in data:
            if row is not None:
                session_id = row['session_id']
                filtered_df = sessions_df[
                    sessions_df["session_id"].str.contains(session_id, case=False)
                ]
                session = filtered_df.iloc[0]
                date = "{}-{}-{}".format(session["last_modified"].year, session["last_modified"].month,
                                         session["last_modified"].day)
                matching_row = team_ratings[team_ratings["Conversation ID"].str.contains(str(session_id))]
                row['user rating'] = "None"
                if not matching_row.empty:
                    row['user rating'] = matching_row["Rating"].iloc[0]
                row['date'] = date
                completed_ratings.append(row)

        changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]

        if completed_ratings != [] and "btn-download-ratings" in changed_id:
            df = pd.DataFrame(completed_ratings)
            logger.info('Downloaded ratings ...')
            return dcc.send_data_frame(df.to_csv, "my_ratings.csv")