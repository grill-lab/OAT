import os
import pandas as pd
import dash_bootstrap_components as dbc

from utils import ComposedDB
from taskmap_pb2 import Session, ConversationTurn
from searcher_pb2 import SearchLog
from conversations_tab_callback import register_conv_callbacks
from search_tab_callbacks import register_search_callbacks

from boto3.dynamodb.conditions import Key
from dash import html, dcc, Dash, callback_context
from datetime import timedelta, datetime
from waitress import serve

from src import (
    get_session_attributes,
    read_database,
    LayoutGenerator,
    Extractor
)

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

if os.path.isfile("annotator_ratings.csv"):
    team_ratings = pd.read_csv("annotator_ratings.csv")
else:
    team_ratings = pd.DataFrame(columns=['Rating', 'Conversation ID'])

# add callbacks
register_conv_callbacks(app, sessions_df, search_logs_df, team_ratings)
register_search_callbacks(app, sessions_df, search_logs_list)

if __name__ == "__main__":
    # app.run_server(debug=True, port=7500, host="0.0.0.0")
    serve(app.server, port=7500, host="0.0.0.0", threads=6)
