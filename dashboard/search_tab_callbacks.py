from dash import html, dcc, Dash, callback_context
from dash.dependencies import Input, Output, State, ALL, MATCH
from utils import logger

import plotly.express as px
import pandas as pd


from src import (
    get_click_through,
    get_search_count,
    get_reformulated_search,
    get_most_common_intents,
    get_nothing_count,
    get_search_logs,
    log_intent_parser
)


def register_search_callbacks(app, sessions_df, search_logs_list):
    @app.callback(
        Output("generated_search_logs", "children"),
        Output("common_intents", "figure"),
        Output("search_phase", "figure"),
        Output("search_click_through", "figure"),
        Output("search_reformulate", "figure"),
        Output("more_results_percentage", "figure"),
        Input("load_search_queries", "n_clicks")
    )
    def update_search_tab(n_clicks):
        """ total_outputs = [ [ {'time': '', 'system': '', 'intent_pred': '', 'user': ''} ] ] """
        logger.info('Getting search logs..')
        search_logs = get_search_logs(search_logs_list)
        total_outputs = log_intent_parser(sessions_df)

        most_common_intent, all_search_queries = get_most_common_intents(total_outputs)
        most_common_intent_df = pd.DataFrame.from_dict(most_common_intent, orient='index')
        most_common_intent_bar = px.bar(most_common_intent_df)

        click_through = get_click_through(total_outputs)
        click_through_df = pd.DataFrame(click_through, columns=["counts"],index=["Selects","Total Searches"])
        click_through_pie = px.pie(click_through_df, values="counts")

        search_count = get_search_count(total_outputs)
        search_count_df = pd.DataFrame(search_count, columns=["counts"],index=["Searches","Sessions"])
        search_count_pie = px.pie(search_count_df, values="counts")

        reformulated_count = get_reformulated_search(total_outputs)
        reformulated_count_df = pd.DataFrame(reformulated_count, columns=["counts"],index=["Reformulated Searches","Searches"])
        reformulated_count_pie = px.pie(reformulated_count_df, values="counts")

        nothing_after_search = get_nothing_count(total_outputs)
        nothing_after_search_df = pd.DataFrame(nothing_after_search, columns=["counts"],index=["get in search","Number of users"])
        nothing_after_search_pie = px.pie(nothing_after_search_df, values="counts")

        return (
            html.Div(search_logs),
            most_common_intent_bar,
            search_count_pie,
            click_through_pie,
            reformulated_count_pie,
            nothing_after_search_pie
        )