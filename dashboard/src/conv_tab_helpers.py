# This contains the dashboard's helper functions
from typing import List, Dict, Union
from dateutil import parser
from datetime import timedelta, datetime
from dash import html, dcc

import itertools
from utils import timeit


def get_conversation_text(turns: List) -> str:
    """
    Concatenates all the text in a session, used for search in the dashboard
    """

    text = ""

    for turn in turns:
        user_interaction = turn["user_request"]["interaction"]
        user_text = user_interaction.get("text")
        if user_text:
            text += user_text + " "

        agent_response = turn["agent_response"]["interaction"]
        speech_text = agent_response.get("speech_text")
        if speech_text:
            text += speech_text + " "

    return text


def get_session_latency(turns: List) -> timedelta:
    """
    Get overall latency for a session
    """

    total_difference = timedelta()

    for turn in turns:

        user_request_time = turn["user_request"].get("time")
        bot_response_time = turn["agent_response"].get("time")

        # if we have time for user request, then we have time for bot response
        if user_request_time:
            total_difference += parser.parse(bot_response_time) - parser.parse(
                user_request_time
            )

    return total_difference


def get_user_and_agent_utterance(session_turn: Dict, turn_ids: List, session_id: str) -> Union[html.P, html.P, html.P, html.P]:
    """
    Parse out user and bot utterances for display on dashboard
    """

    user_interaction = session_turn["user_request"]["interaction"]
    user_text = user_interaction.get("text", "NO USER TEXT")
    user_text_to_display = html.P([html.Strong("User:"), html.P(user_text)])
    system_intent_classification = session_turn["user_request"]["interaction"]
    intents = system_intent_classification.get('intents', [])
    params = system_intent_classification.get('params', [])
    text = system_intent_classification.get('text', "")
    filtered_classification = {"intents": intents, "params": params, "text": text}

    user_time = session_turn["user_request"].get("time")
    parsed_user_time = datetime.strptime(user_time, "%Y-%m-%dT%H:%M:%S.%fZ")

    agent_response = session_turn["agent_response"]["interaction"]
    bot_text = agent_response.get("speech_text", "NO SPEECH TEXT")
    bot_text_to_display = html.P([html.Strong("Bot:")])
    if session_turn['id'] in turn_ids:
        bot_text_to_display.children.append(
            html.P(
                bot_text,
                id={
                    'type': 'search_log',
                    'index': session_turn['id'],
                    'session_id': session_id
                }
            )
        )
    else:
        bot_text_to_display.children.append(html.P(bot_text))

    bot_time = session_turn["agent_response"].get("time")
    parsed_bot_time = datetime.strptime(bot_time, "%Y-%m-%dT%H:%M:%S.%fZ")

    turn_latency = parsed_bot_time - parsed_user_time
    latency = html.P([html.I(f"{turn_latency.total_seconds()} secs")])
    classification = html.P([html.I(f'{filtered_classification}')])

    return user_text_to_display, bot_text_to_display, latency, classification


def get_session_attributes(session: Dict, turn_ids: List, data: Dict) -> html.Div:

    """
    Extract key attributes of a session
    """

    id = session["session_id"]
    session_id = [
        html.H5(f"Conversation ID: {id[:25]}")
    ]
    last_modified = [
        html.H5(
            "Date: {}-{}-{} {}:{}:{}".format(
                session["last_modified"].year,
                session["last_modified"].month,
                session["last_modified"].day,
                session["last_modified"].hour,
                session["last_modified"].minute,
                session["last_modified"].second,
            )
        )
    ]

    rating = [html.H5("Rating: No Rating")]
    conversation_rating = session.get("Rating", None)
    device_type = [html.H5(f"Device Type: {session['headless']}")]
    download_button = [html.Button("Download Session", id={"type": "btn-download-csv", "index": 0, "session_id": id[:25]})]
    download_function = [dcc.Download(id={"type": "download-csv", "index": 0, "session_id": id[:25]})]

    value = 'No Rating'
    for row in data:
        if row is not None:
            if id[:25] in row['session_id']:
                value = row['rating']

    our_rating_slider = [html.Div([
        dcc.Store(id={"type": "memory", "index": 0, "session_id": id[:25]}),
        dcc.Slider(min=0, max=5, step=1, marks={0: "No Rating", 1: "1 Rating", 2: "2 Rating", 3: "3 Rating",
                                                4: "4 Rating", 5: "5 Rating"}, value=value,
                   id={"type": "rating-slider", "index": 0, "session_id": id[:25]})
    ])]
    if conversation_rating != 0:
        rating = [html.H5(f"User Rating: {conversation_rating}")]
    utterances = [get_user_and_agent_utterance(turn, turn_ids, id) for turn in session["turn"]]
    flattened_utterances = list(itertools.chain(*utterances))

    div_children = (
        session_id + device_type + last_modified + rating + flattened_utterances + our_rating_slider +
        download_button + download_function + [html.Hr()]
    )

    return html.Div(div_children)


def get_search_logs(search_logs_list: List):

    search_htmls = []
    for log in search_logs_list:
        search_query = log["search_query"]
        domain = [html.H5(f'Domain: {search_query["domain"]}')]
        session_id = [html.H5(f'Session ID: {search_query["session_id"]}')]
        text = [html.H5(f'Query: {search_query["text"]}')]

        log_html = (domain + session_id + text + [html.Hr()])
        search_htmls.append(html.Div(log_html))
    return search_htmls


@timeit
def read_database(db, filter=None):
    """
    Pull contents of dynamodb database, given a filter
    """
    retrieved_ids = list(db.scan_ids(scan_filter=filter))
    items_list = []
    items_list = db.batch_get(retrieved_ids, decode=False)
    return items_list
