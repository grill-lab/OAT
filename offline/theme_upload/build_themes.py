import json

import tqdm
from google.protobuf.json_format import MessageToDict, Parse, ParseDict
from pyserini.search.lucene import LuceneSearcher

from searcher_pb2 import TaskMapList
from taskmap_pb2 import TaskMap
from semantic_searcher_pb2 import ThemeMapping
from theme_pb2 import ThemeResults
from utils import logger, ProtoDB


class ThemeBuilder:
    def __init__(
        self,
        index_sparse_path: str,
        index_objects_path: str,
        theme_json_path: str,
        theme_data_output_path: str,
        upload_themes: bool,
        db_prefix: str = "Undefined",
        db_url: str = "http://dynamodb-local:8000",
    ) -> None:
        self.index_sparse_path = index_sparse_path
        self.index_objects_path = index_objects_path
        self.theme_json_path = theme_json_path
        self.theme_data_output_path = theme_data_output_path
        self.upload_themes = upload_themes
        self.db_prefix = db_prefix
        self.db_url = db_url

    def upload(self):
        theme_db = ProtoDB(
            proto_class=ThemeResults,
            prefix=self.db_prefix,
            primary_key="theme_word",
            url=self.db_url,
        )

        mapping_db = ProtoDB(ThemeMapping, primary_key="theme_query", prefix="Curated", url=self.db_url)

        with open(self.theme_data_output_path, "r") as file:
            data = json.load(file)

        # save previous recommendation as normal theme
        previous_recommendation = theme_db.get("current_recommendation")
        previous_recommendation.theme_word = previous_recommendation.description
        previous_recommendation.description = ""
        if len(previous_recommendation.theme_word) > 0:
            theme_db.put(previous_recommendation)

        # loop through all themes, save them
        for theme, contents in tqdm.tqdm(data.items(), desc="Saving themes to database"):
            # create a theme mapping between theme query and theme name (needed for semantic searcher)
            if theme != "current_recommendation":
                theme_mapping = ThemeMapping()
                theme_mapping.theme_query = theme
                theme_mapping.theme = theme
                mapping_db.put(theme_mapping)

                if "Day" in theme and "National" in theme:
                    without_day = theme.split(" Day")[0]
                    theme_mapping = ThemeMapping()
                    theme_mapping.theme_query = without_day
                    theme_mapping.theme = theme
                    mapping_db.put(theme_mapping)

                    without_day_and_national = without_day.split("National ")[1]
                    theme_mapping = ThemeMapping()
                    theme_mapping.theme_query = without_day_and_national
                    theme_mapping.theme = theme
                    mapping_db.put(theme_mapping)

                    nationwide = theme.replace("National", "Nationwide")
                    theme_mapping = ThemeMapping()
                    theme_mapping.theme_query = nationwide
                    theme_mapping.theme = theme
                    mapping_db.put(theme_mapping)

                    without_day_and_national_lower = without_day_and_national.lower()
                    theme_mapping = ThemeMapping()
                    theme_mapping.theme_query = without_day_and_national_lower
                    theme_mapping.theme = theme
                    mapping_db.put(theme_mapping)

            # upload each theme to themes database
            obj = ThemeResults()
            obj.theme_word = theme
            if contents.get("candidates", None) is not None:
                ParseDict({"candidates": contents["candidates"]}, obj.results)
            obj.description = contents["description"]
            obj.popular_tasks.extend(contents.get("popular_tasks", []))
            obj.intro_sentence = contents.get("intro_sentence", "")
            obj.alternative_description = contents.get("alternative_description", "")
            obj.date = contents.get("date", "")
            obj.hand_curated = contents.get("hand_curated", False)
            obj.thumbnail = contents.get("thumbnail", "")
            theme_db.put(obj)

    def run(self) -> None:
        theme_recommendations = json.load(open(self.theme_json_path))

        searcher = LuceneSearcher(index_dir=self.index_sparse_path)
        searcher.set_bm25(b=0.4, k1=0.9)
        searcher.set_rm3(fb_terms=10, fb_docs=10, original_query_weight=0.5)
        taskgraph_retriever = LuceneSearcher(index_dir=self.index_objects_path)

        theme_recommendations_protos = {k: TaskMapList() for k in theme_recommendations}

        # iterate through the list of predefined themes
        for theme_name, theme_info in tqdm.tqdm(theme_recommendations.items(), desc="Finding theme recommendations"):
            if "recipes" not in theme_info or len(theme_info["recipes"]) == 0:
                logger.info(f"Skipping theme {theme_name}")
                continue

            for recipe_name in theme_info["recipes"]:
                # search using the recipe name
                logger.info(f"Searching for {theme_name} matches using '{recipe_name}'")
                hits = searcher.search(q=recipe_name, k=1)

                if len(hits) == 0:
                    logger.info(f"No hits for {recipe_name}!")
                    continue

                logger.info(f"Found TaskGraph for {recipe_name}")
                hit = hits[0]
                logger.info(f"Retrieving TaskGraph with ID {hit.docid}")
                doc = taskgraph_retriever.doc(docid=hit.docid)
                if doc is None:
                    logger.warning(f"Failed to retrieve TaskGraph with ID {hit.docid}!")
                    continue
                doc_json = json.loads(doc.raw())
                obj_json = doc_json["document_json"]
                taskmap = TaskMap()
                Parse(json.dumps(obj_json), taskmap)
                theme_recommendations_protos[theme_name].candidates.extend([taskmap])

        for theme in theme_recommendations_protos:
            theme_recommendations_protos[theme] = MessageToDict(theme_recommendations_protos[theme])
            theme_recommendations_protos[theme]["description"] = theme_recommendations[theme]["description"]
            theme_recommendations_protos[theme]["date"] = theme_recommendations[theme].get("date", "")
            theme_recommendations_protos[theme]["intro_sentence"] = theme_recommendations[theme].get("intro_sentence", "")
            theme_recommendations_protos[theme]["alternative_description"] = theme_recommendations[theme].get(
                "alternative_description", ""
            )
            theme_recommendations_protos[theme]["hand_curated"] = theme_recommendations[theme].get("hand_curated", False)
            theme_recommendations_protos[theme]["popular_tasks"] = theme_recommendations[theme].get("popular_tasks", [])
            theme_recommendations_protos[theme]["thumbnail"] = theme_recommendations[theme].get("thumbnail", "")

        with open(self.theme_data_output_path, "w") as f:
            json.dump(theme_recommendations_protos, f, indent=4)

        if self.upload_themes:
            self.upload()
