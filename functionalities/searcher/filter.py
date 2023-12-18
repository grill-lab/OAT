from taskmap_pb2 import TaskMap, Session
from utils import logger


def filter_taskmap(taskmap: TaskMap):
    """ return True is valid else False if not"""

    if not taskmap.title:
        return False

    if not taskmap.steps:
        return False

    num_requirements = 0 if not taskmap.requirement_list else len(taskmap.requirement_list)
    if num_requirements > 20:
        return False

    num_steps = 0 if not taskmap.steps else len(taskmap.steps)
    if num_steps > 20:
        return False

    max_step_words = max([len(step.response.speech_text.split()) for step in taskmap.steps])
    if max_step_words > 100:
        return False

    min_step_words = min([len(step.response.speech_text.split()) for step in taskmap.steps])
    if min_step_words == 0:
        return False

    return True


def filter_wikihow_cooking(query, taskmap: TaskMap):
    if query.domain == Session.Domain.COOKING and taskmap.dataset in {"wikihow-offline", "wikihow"}:
        logger.info(f"{taskmap.title} is from {taskmap.dataset}")
        return False
    else:
        return True
