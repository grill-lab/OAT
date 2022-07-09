from ..abstract_parser import AbstractParser
from taskmap_pb2 import Session
from utils import indri_stop_words, theme_recommendations


class VagueParser(AbstractParser):

    def __call__(self, session: Session) -> Session:
        query = session.turn[-1].user_request.interaction.text

        """ Assert whether query a theme query (i.e. words map to specified theme). """
        # Find specific words by removing stopwords.
        vague_words = [
            'build', 'bake', 'quick', '', 
            'home', 'improvement', 'homeimprovement', 
            'fix', 'eat', 'search', 'stuff', "recommend",
            "okay"
        ]
        disfluencies = [
            "uh", "um", "uhm"
        ]
        stopwords = indri_stop_words + vague_words + disfluencies
        specific_words = [s.lower() for s in query.split(" ") if s.lower() not in stopwords]

        themes = theme_recommendations.keys()
        theme_words = [w for w in specific_words if w in themes]
        param = None

        if len(specific_words) == 0:
            # vague query
            intent = "VagueSearchIntent"

        elif len(theme_words) == len(specific_words):
            # theme search
            intent = "ThemeSearchIntent"
            param = theme_words
        else:
            # specific search
            intent = "SpecificSearchIntent"

        session.turn[-1].user_request.interaction.intents.append(intent)
        if param is not None:
            session.turn[-1].user_request.interaction.params.extend(param)

        return session
