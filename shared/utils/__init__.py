from .main_logging import logger

from .general import get_server_interceptor
from .general import get_interceptors
from .general import log_latency
from .general import init
from .general import log_latency
from .general import get_file_system
from .general import get_taskmap_id

from .session import get_credit_from_taskmap
from .session import get_credit_from_url
from .session import close_session
from .session import consume_intents
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
from .session import set_source
from .session import get_helpful_prompt
from .session import get_recommendations
from .session import should_trigger_theme

from .search import theme_recommendations

from .screen import build_chat_screen
from .screen import build_help_grid_screen
from .screen import build_farewell_screen
from .screen import get_helpful_options
from .screen import build_default_screen
from .screen import build_joke_screen
from .screen import compile_joke_screen

from .downloads import Downloader

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
