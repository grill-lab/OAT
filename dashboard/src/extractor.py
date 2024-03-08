import pandas as pd
import numpy as np
from . import get_conversation_text, get_session_latency

class Extractor():

    def extract_session_attributes(self, df: pd.DataFrame) -> pd.DataFrame:

        """
        Extract/modify useful attributes of sessions
        """

        df["last_modified"] = df.apply(
            lambda row: row["turn"][-1]["agent_response"].get("time"), axis=1
        )

        # change date to datetime format
        df["last_modified"] = pd.to_datetime(
            df["last_modified"], format="%Y-%m-%d"
        )

        # get length of conversation
        df["conversation_length"] = df.apply(
            lambda session: len(session.get("turn", [])), axis=1
        )

        # get the phase the user dropped off
        df["phase"] = df.apply(
            lambda row: row["task"].get("phase") if row.get("task", np.nan) is not np.nan else "DOMAIN",
            axis=1,
        )
        df["phase"].fillna(value="DOMAIN", inplace=True)

        # get ths device the user is on
        if "headless" not in df.columns:
            df["headless"] = [None] * len(df)  # fill it with None if it empty
        df["headless"].fillna(value=False, inplace=True)
        df["headless"] = df["headless"].map(
            {True: "Headless", False: "Screen"}
        )
        if "domain" not in df.columns:
            df["domain"] = ["NOT SELECTED"] * len(df)  # fill it with None if it is empty
        else:
            # if there's no domain, then it was not selected
            df["domain"].fillna(value="NOT SELECTED", inplace=True)

        # if there's no state, then the session is still open
        if "state" not in df.columns:
            df["state"] = [None] * len(df)  # fill it with None if it is empty
        df["state"].fillna(value="OPEN", inplace=True)

        # if there's no greetings, then it should be false
        df["greetings"].fillna(value=False, inplace=True)

        # retrieve conversation text
        df["conversation_text"] = df.apply(
            lambda row: get_conversation_text(row["turn"]), axis=1
        )

        # get latency of the session
        df["latency"] = df.apply(
            lambda row: get_session_latency(row["turn"]), axis=1
        )

        return df
    
    def extract_search_log_ids(self, df: pd.DataFrame) -> pd.DataFrame:

        """
        Extract session_id and turn_id from search logs for easier mapping
        """

        # extract indentifiers
        df["session_id"] = df.apply(
            lambda row: row["search_query"].get("session_id") , axis=1
        )
        df["turn_id"] = df.apply(
            lambda row: row["search_query"].get("turn_id") , axis=1
        )
        
        return df