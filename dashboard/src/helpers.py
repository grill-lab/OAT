# This contains the dashboard's helper functions
from typing import List, Dict, Union
from dateutil import parser

from datetime import timedelta, datetime
from dash import html
import dash_bootstrap_components as dbc

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


def get_user_and_agent_utterance(session_turn: Dict, turn_ids: List, session_id: str) -> Union[html.P, html.P, html.P]:
    """
    Parse out user and bot utterances for display on dashboard
    """

    user_interaction = session_turn["user_request"]["interaction"]
    user_text = user_interaction.get("text", "NO USER TEXT")
    user_text_to_display = html.P([html.Strong("User:"), html.P(user_text)])
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

    return user_text_to_display, bot_text_to_display, latency


def get_session_attributes(session: Dict, turn_ids: List) -> html.Div:

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

    # rating = [html.H5("Rating: No Rating")]
    # conversation_rating = session["Rating"]
    device_type = [html.H5(f"Device Type: {session['headless']}")]
    #
    # if conversation_rating != 0:
    #     rating = [html.H5(f"Rating: {conversation_rating}")]
    utterances = [get_user_and_agent_utterance(turn, turn_ids, id) for turn in session["turn"]]
    flattened_utterances = list(itertools.chain(*utterances))

    div_children = (
        session_id + device_type + last_modified + flattened_utterances + [html.Hr()]
    )

    return html.Div(div_children)

@timeit
def read_database(db, filter):
    """
    Pull contents of dynamodb database, given a filter
    """
    retrieved_ids = db.scan_ids(scan_filter=filter)
    items_list = db.batch_get(retrieved_ids, decode=False)
    return items_list
