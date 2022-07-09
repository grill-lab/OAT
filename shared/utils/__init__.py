from .logging import logger

from .general import get_server_interceptor
from .general import init
from .general import get_file_system

from .general import get_taskmap_id
from .general import consume_intents
from .general import jaccard_similarity

from .session import get_credit_from_taskmap
from .session import get_credit_from_url
from .session import close_session
from .session import is_in_user_interaction
from .session import repeat_screen_response
from .session import screen_summary_taskmap
from .session import get_star_string
from .session import format_author
from .session import format_author_headless
from .session import show_ingredients_screen
from .session import headless_task_summary
from .session import format_requirements
from .session import display_screen_results
from .session import populate_choices
from .session import build_video_button
from .session import filter_speech_text

from .search import theme_recommendations

from .nlp import jaccard_sim
from .constants.global_variables import *
from .constants.prompts import *

from .aws.timeit import *

try:
    # if Boto3 is not installed, skip importing ProtoDB and ComposedDB
    from .aws.new_proto_db import ProtoDB
    from .aws.composed_db import ComposedDB
except ImportError as e:
    # logger.info("Boto3 is not installed, skipping ProtoDB from utils!")
    pass

try:
    with open('/shared/utils/indri_stop_words.txt', 'r') as f:
        lines = f.readlines()
        indri_stop_words = [line.rstrip() for line in lines]
except Exception as e:
    pass
