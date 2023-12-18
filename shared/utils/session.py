import inspect
import os
import json
import random
import re
from types import FrameType
from typing import List, Optional, Tuple
from urllib.parse import urlparse
from inspect import getframeinfo, stack
from utils import get_file_system


from taskmap_pb2 import (
    Image,
    OutputInteraction,
    OutputSource,
    ScreenInteraction,
    SessionState,
    TaskMap,
    Session,
    TaskmapCategoryUnion,
    InputInteraction,
    TaskSelection,
    Task
)
from video_document_pb2 import VideoDocument

from .constants.prompts import (
    CATEGORY_PROMPT,
    VIDEO_SUGGESTIONS
)

from . import logger
from .nlp import jaccard_sim

def get_star_string(rating_float: float, rating_count: int):
    """Generates a 5-star rating string for a TaskMap.

    Given an averaged 0-5 rating for a task and the number of ratings
    it was calculated from, this method will return a string containing
    the appropriate number of filled (★) and empty (☆) characters, appending
    the number of individual ratings in parentheses if known.

    Args:
        rating_float (float): the calculated rating for the task
        rating_count (int): the number of ratings (0 if unknown)

    Returns:
        5 filled/empty star characters matching the rating value (str)
    """
    rating_str = ''
    full_star = '&#9733;'
    empty_star = '&#9734;'
    for i in range(1, 6):
        if i <= rating_float:
            rating_str += full_star
        else:
            rating_str += empty_star
    if rating_count != 0:
        return f"{rating_str} ({rating_count})"
    else:
        return f"{rating_str}"


def format_author(author: str) -> str:
    """Formats an author string for display on non-headless devices.

    Given the .author field of a TaskMap, attempts to extract and return
    the most relevant text from it. 

    Args:
        author (str): the .author field content from a TaskMap

    Returns:
        reformatted author text (str)
    """
    if "," in author:
        # if there are any commas, split the string around those 
        # return the first item
        return author.split(",")[0]
    else:
        name_parts = author.split(' ')
        if len(name_parts) > 3:
            # this returns the capitalised first letter of each space-separated word?
            return "".join([f'{a[0].capitalize()}' for a in name_parts if a != ''])
        else:
            # given something like ["one", "two", "three"] this will end up with
            # abbrev containing ["o.", "t.", "three"]
            abbrev = [f'{a[0]}.' for a in name_parts if a != ''][:-1]
            abbrev.append(name_parts[-1])

            if len(" ".join(abbrev)) > 15:
                abbrev = [f'{a[0]}.' for a in name_parts if a != '']
            return " ".join(abbrev)


def format_author_headless(author: str) -> str:
    """Format author string for headless devices.

    This is a simplified version of ``format_author``. If the string
    contains any commas, the string is split around them and the first
    item in the list is returned. Otherwise the string is return as-is.

    Args:
        author (str): the .author field content from a TaskMap

    Returns:
        reformatted author text (str)
    """
    if "," in author:
        return author.split(",")[0]
    else:
        return author


def get_credit_from_url(url: str) -> str:
    """Given a URL, return a name derived from the domain.

    This method uses urllib to parse the raw URL into its component
    parts, then extracts the "netloc" field which contains the domain.

    If the parsing fails, it returns an empty string at this point. 
    Otherwise, the domain is split around "." characters, and if the
    resulting list is less than 2 items long it will return the full
    domain string (e.g. "wikihow.com"). 

    If the string splitting produces >2 items, it will return the 2nd
    item in the list (e.g. for "subdomain.website.com" it would end up
    returning "subdomain").

    Args:
        url (str): the URL string

    Returns:
        the extracted component of the domain name (str)

    """
    domain = urlparse(url).netloc
    if domain:
        website_keyword = domain.split('.')
        if len(website_keyword) > 2:
            website_name = website_keyword[1:-1][0]
        else:
            website_name = domain
        return website_name
    return ''


def get_credit_from_taskmap(taskmap: TaskMap) -> str:
    """Given a TaskMap, return a string indicating the source website.

    This method relies on ``get_credit_from_url``. If the TaskMap has
    a valid .source_url, it will return the result of calling 
    ``get_credit_from_url`` on it. If there is no source_url, it falls
    back to .image_url. If neither is available, an empty string is
    returned instead.

    Args: 
        taskmap (TaskMap): a populated TaskMap object

    Returns:
        the name extracted from the URL(s) in the TaskMap (str)
    """
    source_url = taskmap.source_url
    if source_url:
        website_name = get_credit_from_url(source_url)
        return website_name
    # If no source url -> check thumbnail url as a proxy.
    else:
        image_url = taskmap.thumbnail_url
        website_name = ""
        if image_url:
            website_name = get_credit_from_url(image_url)
            if website_name == "s3":
                website_name = ""
        if taskmap.domain_name != "ai_generated":
            website_name = taskmap.domain_name
        return website_name
    return ''


def close_session(session: Session, output: OutputInteraction) -> Tuple[Session, OutputInteraction]:
    """Helper method for closing an active session with the system.

    Updates some fields of the supplied Session and OutputInteraction
    objects to reflect the closure of the session, then returns the
    updated objects.

    Args:
        session (Session): an active Session object
        output (OutputInteraction): the OutputInteraction to be returned to the user

    Returns:
        tuple(updated Session, updated OutputInteraction object)
    """
    session.state = SessionState.CLOSED
    session.greetings = False  # To greet the user next time
    output.close_interaction = True
    session.task.state.validation_options_displayed = False
    session.task.state.validation_page = 0

    return session, output


def consume_intents(user_interaction: InputInteraction, intents_list: List[str]) -> None:
    """'Consumes' intents from an InputInteraction object.

    InputInteraction objects have a .intents field containing a list of string 
    intent names, e.g. "YesIntent". This method iterates over the list comparing
    each entry with the supplied ``intents_list``. If any of the interaction intents
    appear in ``intents_list``, they are removed and the list has a new entry appended
    containing "Consumed.<intent name>".

    Args:
        user_interaction (InputInteraction): an InputInteraction object from 
            the current Session
        intents_list (List[str]): a list of intent names to check for

    Returns:
        Nothing
    """
    for intent in intents_list:
        if intent in user_interaction.intents:
            user_interaction.intents.remove(intent)
            user_interaction.intents.append('Consumed.'+intent)


def is_in_user_interaction(user_interaction: InputInteraction,
                           *, 
                           intents_list: List[str] = [],
                           utterances_list: List[str] = []):
    """Check if a particular intent or utterance matches an InputInteraction.

    This method is used to check if either:
    
    - any entry in ``intents_list`` appears in the .intents field of the InputInteraction
    - any of the words/phrases in ``utterances_list`` appear in the .text
      field of the InputInteraction (the user's last utterance)

    Both list parameters are optional, so the method can be called with only
    one set as appropriate.

    This method is heavily used in the policy classes to check if the Session
    is in a particular state or if a policy action should be triggered. 

    Args:
        user_interaction (InputInteraction): an InputInteraction object
        intents_list (List[str]): list of intents to check for
        utterances_list (List[str]): list of utterances to check for

    Returns:
        True if any utterances OR any intents matched, False otherwise
    """
    user_intents = user_interaction.intents
    user_utterance = user_interaction.text

    matched_intents = set.intersection(set(user_intents), set(intents_list))
    # return True if there is an utterance match, or any intents matched
    return user_utterance in utterances_list or len(matched_intents) != 0


def repeat_screen_response(session: Session, response: OutputInteraction) -> OutputInteraction:
    """Copies a ScreenInteraction from a previous turn into a new OutputInteraction.

    This method takes the 2nd last turn in the Session object (the last turn is the one
    still in progress) and copies the .agent_response.interaction.screen field into the
    .screen field of the supplied OutputInteraction. This field is a ScreenInteraction 
    object which contains various information for display on non-headless devices. 

    Arguments:
        session (Session): an active Session object
        response (OutputInteraction): an OutputInteraction object

    Returns:
        an updated OutputInteraction object
    """
    if not session.headless and len(session.turn) > 1:
        response.screen.ParseFromString(session.turn[-2].agent_response.interaction.screen.SerializeToString())

    return response


def format_requirements(req_list: List[str]) -> str:
    """Given a TaskMap requirements list, return a formatted HTML string representation.

    (not currently used)

    This method takes a list of task steps from a TaskMap and formats it so that 
    each step is prefixed by a number (or letters if >=10 steps) and suffixed by
    an HTML <br> tag. The final string is created by joining these all together and
    adding "Things you'll need" at the start. 

    Args:
        req_list (List[str]): list of requirements from a TaskMap

    Returns:
        the formatted requirements string
    """
    if len(req_list) > 0:
        ingredients = []
        for i in range(len(req_list)):
            if 0 <= i < 10:
                text = f' &#x246{i}; {req_list[i]}<br>'
                ingredients.append(text)
            elif 10 <= i < 17:
                text = f' &#x246{chr(65+i-10)}; {req_list[i]}<br>'
                ingredients.append(text)
        ingredients_text = " ".join(ingredients)
        req_text = f"<b>Things you'll need:</b><br>{ingredients_text}"
        return req_text
    return ''

def screen_summary_taskmap(taskmap: TaskMap, speech_req: str) -> ScreenInteraction:
    """Populate and return a ScreenInteraction describing a TaskMap.

    Args:
        taskmap (TaskMap): a TaskMap object
        speech_req (str): "ingredients" if the TaskMap is a cooking task,
            "tools and materials" if a DIY task

    Returns:
        a populated ScreenInteraction object
    """
    screen: ScreenInteraction = ScreenInteraction()
    screen.headline = taskmap.title
    screen.format = ScreenInteraction.ScreenFormat.SUMMARY

    taskmap_credit = get_credit_from_taskmap(taskmap)

    image: Image = screen.image_list.add()
    image.path = taskmap.thumbnail_url
    image.title = taskmap.title

    if taskmap.author != "":
        author_string = ''
        author_string += f"by {taskmap.author}"
        if taskmap_credit != "":
            author_string += f' on {taskmap_credit}'
        screen.paragraphs.append(author_string)
    else:
        screen.paragraphs.append(f"by {taskmap_credit}<br/>")

    if taskmap.rating_out_100 is not None and taskmap.rating_out_100 != 0 and taskmap.rating_count is not None:
        rating = taskmap.rating_out_100/20
        image.ratingValue = rating
        # screen.paragraphs.append(f"<b>Rating:</b> {get_star_string(rating, taskmap.rating_count)}")

    if taskmap.difficulty is not None and taskmap.difficulty != "":
        screen.paragraphs.append(f"<b>Difficulty:</b> {taskmap.difficulty}")

    if taskmap.active_time_minutes != 0:
        screen.paragraphs.append(f"<b>Active time:</b> "
                                 f"{convert_minutes_to_hours(taskmap.active_time_minutes)}")
    if taskmap.total_time_minutes != 0:
        screen.paragraphs.append(f"<b>Total time:</b> "
                                 f"{convert_minutes_to_hours(taskmap.total_time_minutes)}")

    if taskmap.serves != '' and taskmap.serves is not None and taskmap.serves != "None":
        screen.paragraphs.append(f"<b>Serves:</b> {taskmap.serves.replace('Serves', '').replace(':', '').strip()}")

    if len(taskmap.requirement_list) > 0:
        screen.paragraphs.append(f"<b>Requires:</b> {len(taskmap.requirement_list)} {speech_req}")

    if len(taskmap.steps) > 0:
        screen.paragraphs.append(f"<b>Number of steps:</b> {len(taskmap.steps)}")

    if taskmap.description != '':
        if len(taskmap.description.split(" ")) <= 50:
            screen.paragraphs.append(f"<b>Description:</b> {taskmap.description}")
    elif taskmap.voice_summary != '':
        screen.paragraphs.append(f"<b>Description:</b> {taskmap.voice_summary}")

    return screen


def headless_task_summary(taskmap: TaskMap, speech_req: str) -> str:
    """Generate a plaintext summary of a TaskMap for headless devices.

    This is the headless version of ``screen_summary_taskmap``. 

    Args:
        taskmap (TaskMap): a TaskMap object
        speech_req (str): "ingredients" if the TaskMap is a cooking task,
            "tools and materials" if a DIY task

    Returns:
        a summary of the Taskmap (str)
    """
    speech_output = f'You chose {taskmap.title}'

    if taskmap.author != "":
        speech_output += f" by {format_author_headless(taskmap.author)}"
    else:
        taskmap_credit = get_credit_from_taskmap(taskmap)
        if taskmap_credit != "":
            speech_output += f' by {taskmap_credit}'

    if taskmap.rating_out_100 is not None and taskmap.rating_out_100 != 0 and taskmap.rating_count is not None:
        rating = taskmap.rating_out_100 / 20
        speech_output += f". It's got a rating of {rating:.1f} stars"

    if taskmap.serves != '' and taskmap.serves is not None and taskmap.serves != "None":
        try:
            speech_output += f", serves {float(taskmap.serves):.0f} people"
        except:
            speech_output += f", serves {taskmap.serves}"

    if taskmap.rating_out_100 is not None and taskmap.rating_out_100 != 0 \
            and taskmap.serves is not None and taskmap.serves != "None":
        if len(taskmap.steps) > 1:
            speech_output += f" and has {len(taskmap.steps)} steps"
        elif len(taskmap.steps) == 1:
            speech_output += f" and has {len(taskmap.steps)} step"
    else:
        speech_output += f". This task has {len(taskmap.steps)} steps"

    if taskmap.difficulty is not None and taskmap.difficulty != "":
        speech_output += f" . The difficulty is {taskmap.difficulty}"

    if taskmap.active_time_minutes != 0:
        speech_output += f". It also has an active cooking time of " \
                         f"{convert_minutes_to_hours(taskmap.active_time_minutes)}"
    if taskmap.total_time_minutes != 0:
        if taskmap.active_time_minutes != 0:
            speech_output += f" and will take {convert_minutes_to_hours(taskmap.total_time_minutes)} in total"
        else:
            speech_output += f". {taskmap.title} will take " \
                             f"{convert_minutes_to_hours(taskmap.total_time_minutes)} in total"

    if len(taskmap.requirement_list) > 0:
        speech_output += f". By the way, you will need {len(taskmap.requirement_list)} {speech_req}"

    return speech_output


def convert_minutes_to_hours(minutes: int) -> str:
    """Converts a number of minutes to a string representation.

    If the number of minutes is under 60, this will simply return 
    "x minutes". If the number of minutes is over 60, it will
    return "x hours and y minutes". 

    Args:
        minutes (int): number of minutes in time span

    Returns:
        formatted string as described above
    """
    if minutes > 60:
        hours = minutes // 60
        remaining_minutes = minutes % 60
        time_str = f"{hours} hour"
        if hours > 1:
            time_str += "s"
        if remaining_minutes != 0:
            time_str += f" and {remaining_minutes} minutes"
    else:
        time_str = f"{minutes} minutes"
    return time_str


def show_ingredients_screen(session: Session, requirements_list: List[str], response: OutputInteraction) -> OutputInteraction:
    """Generate an OutputInteraction set up to show ingredients/tools required for a task.

    If the supplied ``requirements_list`` is empty, this method will just call the
    ``repeat_screen_response`` method to copy the previous ScreenInteraction object
    into a new OutputInteraction. 

    If ``requirements_list`` is not empty, it populates a ScreenInteraction directly
    and adds that to the returned OutputInteraction.

    Args:
        session (Session): an active Session object
        requirements_list (List[str]): list of requirements (may be empty)
        response (OutputInteraction): an OutputInteraction object

    Returns:
        a new/updated OutputInteraction
    """
    taskmap = session.task.taskmap

    if requirements_list != []:
        output: OutputInteraction = OutputInteraction()
        screen: ScreenInteraction = ScreenInteraction()
        screen.headline = taskmap.title
        screen.format = ScreenInteraction.ScreenFormat.TEXT_IMAGE

        image: Image = screen.image_list.add()
        image.path = taskmap.thumbnail_url
        image.title = taskmap.title
        screen.requirements.extend(requirements_list)
        output.screen.ParseFromString(screen.SerializeToString())
        set_source(output)
    else:
        output: OutputInteraction = repeat_screen_response(session, response)
        set_source(output)

    return output


def populate_comparison_options(options, candidates, domain):
    _, max_rating, min_duration = get_recommendations(candidates=candidates, domain=domain)
    for idx, candidate in enumerate(candidates):
        if candidate == max_rating:
            options[idx] = "Best Rated"
        elif candidate == min_duration:
            options[idx] = "Quickest"

    return options


def display_screen_results(candidates: List[TaskmapCategoryUnion], output: OutputInteraction,
                           domain: Session.Domain) -> List[str]:
    """Takes a list of TaskMap candidates and format them for display/clicking.

    This method constructs an Image proto object for each of the candidate TaskMaps,
    populating each one with the relevant information from the TaskMap. The new
    objects are added to the ScreenInteraction inside the supplied OutputInteraction.
    The return value is a list of integers in string format ranging from 
    1 -- len(candidates).

    These data structures are ultimately used to display clickable objects on 
    a non-headless client device. The Images provide the data to be displayed 
    (they contain both images and text fields) while the "on_click_list" is used
    as a parameter in client click handlers to link the clicked item to the right
    entry in the candidates list (e.g. clicking the first item would mean the click
    handler gets the "1" from the click list, and this can be used to get back to 
    the TaskMap in the candidates list). 

    Args:
        candidates (List[TaskMap]): a list of candidate TaskMaps for the current search
        output (OutputInteraction): the OutputInteraction about to be returned to the user

    Returns:
        a list of click indexes in string format, ranging from 1 -- len(candidates)
    """
    output.screen.format = ScreenInteraction.ScreenFormat.IMAGE_CAROUSEL

    on_click_list = []

    options = ["Currently Trending", "Expert Tested", "Timeless Classic"]
    candidate_found = any([cand.HasField('category') for cand in candidates])
    if candidate_found:
        options = populate_comparison_options(options, candidates[:2], domain)
    else:
        options = populate_comparison_options(options, candidates, domain)

    for idx, candidate in enumerate(candidates):
        image: Image = output.screen.image_list.add()

        if candidate.HasField('category'):
            image.path = candidate.category.sub_categories[0].candidates[0].image_url
            image.title = candidate.category.title
            image.description = "Our Recommendations"
            if domain == Session.Domain.COOKING:
                image.description = "Recipe Finder"
            else:
                image.description = "Task Finder"
            on_click_list.append(str(idx+1))
        else:
            candidate = candidate.task
            image.tags.extend(__concatenate_tags(candidate))
            image.path = candidate.thumbnail_url
            image.title = candidate.title
            image.description = options[idx]
        on_click_list.append(str(idx+1))
    
    return on_click_list

def __concatenate_tags(taskmap: TaskMap) -> List[str]:
    tags = [tag for tag in taskmap.tags]
    # Get max number of tags possible
    tag_count = 0
    while len(tags) >= tag_count and len("".join(tags[:tag_count+1])) < 33 - tag_count * 3:
        tag_count += 1
        
    return tags[:tag_count]
  

def populate_choices(candidates: List[TaskmapCategoryUnion]) -> str:
    """Generate text listing basic details of a list of TaskMaps.

    Given a list of TaskMaps, this method generates a string for each one
    along the lines of "<title> by <author>/<website name>", and inserts
    short linking phrases to enumerate them ("First is X, second is Y" etc).

    If more than 3 TaskMaps are passed in, it will only include the first 3
    in the result. 

    Args:
        candidates (List[TaskMap]): a list of TaskMap objects

    Returns:
        a string combining the basic information about each TaskMap
    """
    speech_text = ''
    idx: int
    ordinal_phrases = [
        ["The first one is", "The second option is", "And, finally"],
        ["First is", "Second is", "And, third"]
    ]
    ordinals = random.choice(ordinal_phrases)
    # note, only taking the first 3 entries here
    for idx, candidate in enumerate(candidates[:3]):
        if type(candidate) != TaskMap:
            result = f"{getattr(candidate, candidate.WhichOneof('candidate')).title}"
            if candidate.HasField('category'):
                candidate = candidate.category
                if idx == 2:
                    speech_text += random.choice(CATEGORY_PROMPT).format(result)
                else:
                    logger.warning(f"Category should only by in 3rd position in search results but found in position {idx+1}")
                    speech_text += f'{ordinals[idx]}: {result}. '
            else:
                candidate = candidate.task
                if candidate.author is not None and candidate.author != "":
                    result += f" by {format_author_headless(candidate.author)}"
                elif candidate.domain_name is not None and candidate.domain_name != "":
                    result += f" by {candidate.domain_name}"
                speech_text += f'{ordinals[idx]}: {result}. '
        else:
            result = candidate.title
            if candidate.author is not None and candidate.author != "":
                result += f" by {format_author_headless(candidate.author)}"
            elif candidate.domain_name is not None and candidate.domain_name != "":
                result += f" by {candidate.domain_name}"
            speech_text += f'{ordinals[idx]}: {result}. '
            
    return speech_text


def build_video_button(output: OutputInteraction, video: VideoDocument, video_suggested = True) -> Tuple[str, ScreenInteraction]:
    """Construct a ScreenInteraction to set up a clickable video element on the client.

    This method initially copies the existing ScreenInteraction from the supplied
    OutputInteraction, then (if the VideoDocument has a non-empty title) it will
    populate the necessary fields of the ScreenInteraction, and construct a simple
    prompt to display/say to the user incorporating the video title.

    Args:
        output (OutputInteraction): the current OutputInteraction object
        video (VideoDocument): information about a video for the current task

    Returns:
        tuple(text to display to the user, new ScreenInteraction)
    """

    screen = ScreenInteraction()
    screen.ParseFromString(output.screen.SerializeToString())
    speech_text = ""

    if video.title != "":
        if 0 < len(screen.buttons) < 1:
            temp = screen.buttons[0]
            screen.buttons.append(temp)
        elif len(screen.buttons) == 0:
            screen.buttons.append('Video')
            screen.on_click_list.append('play video')

        screen.buttons[0] = 'Video'
        screen.on_click_list[0] = 'play video'

        if len(screen.buttons) == 1:
            screen.buttons.append('Next')
            screen.on_click_list.append('Next')

        screen.hint_text = 'play video'

    return speech_text, screen


def filter_speech_text(speech_text: str) -> str:
    """Corrects some potential issues with characters in speech text.

    This method does a couple of search/replace operations on the original text:
     
    - change instances of "<1 or more digits>F" by inserting a "º" before the "F",
      e.g. "123F" becomes "123ºF"
    - change instances of " degrees F." to "ºF."

    Args:
        speech_text (str): original speech text string

    Returns:
        possibly updated string as described above
    """
    replace_regexes = [(r'((\d)+).?F', r'\1ºF')]
    for find_reg, replace_with in replace_regexes:
        speech_text = re.sub(find_reg, replace_with, speech_text)

    speech_text = speech_text.replace(" degrees F.", "ºF.")
    return speech_text

def set_source(output: OutputInteraction, msg: str = "", overwrite: bool = False) -> OutputInteraction:
    """Populates the .source field of an OutputInteraction object.

    This method is used to tag policy responses with the location in
    the code where they were created, to aid in debugging/tracing of
    unknown or unexpected responses from the system.

    The OutputInteraction.source field is an instance of OutputSource.
    This contains fields that will be set as follows:
        policy: name of the policy module without extension (e.g. 'domain_policy')
        filename: full path of the module
        line_number: line number in the policy module where this method was called
        message: set from the ``msg`` parameter, may be empty

    Args:
        output (OutputInteraction): the output interaction to be populated
        msg (str): an optional additional message to include
        overwrite (bool): if False, check if the .source field of the supplied
            OutputInteraction has already been populated, and return it immediately
            if so (default). Otherwise a new OutputSource object is constructed and
            copied into the field.

    Returns:
        Updated OutputInteraction object

    """

    # to avoid accidentally overwriting an already-populated object, check
    # if the policy field has been set already
    if not overwrite and len(output.source.policy) > 0:
        logger.warning("Refusing to overwrite OutputInteraction.source")
        return output

    # To retrieve the information about the policy which called this
    # method, we need the previous stack frame instead of the current
    # one which corresponds to the call to this method. Calling
    # inspect.currentframe() gives the current frame, then .f_back
    # will give the previous frame (https://docs.python.org/3/library/inspect.html)
    cur_frame: Optional[FrameType] = inspect.currentframe()
    if cur_frame is None or cur_frame.f_back is None:
        logger.warning("Failed to retrieve frame information!")
        return output

    last_frame: FrameType = cur_frame.f_back

    # the full path+filename of the module where this method was
    # called from, for example:
    #   /source/policy/domain_policy/domain_policy.py
    full_filename: str = last_frame.f_code.co_filename
    # trim this down to just the filename without the extension
    # to set the policy field
    filename = os.path.split(full_filename)[1]
    policy: str = os.path.splitext(filename)[0]

    source = OutputSource()
    source.policy = policy
    source.filename = full_filename
    source.line_number = last_frame.f_lineno
    source.message = msg
    output.source.CopyFrom(source)
    return output


def get_helpful_prompt(phase, task_title: str, task_selection: TaskSelection, headless=False):
    # phase = session.task.phase
    # task_title = session.task.taskmap.title
    # task_selection = session.task_selection
    # headless = session.headless

    tutorial_list = []

    tutorial_list.append(f"If you want to exit the conversation, just say exit")
    tutorial_list.append(f"If you need any guidance with what I can do, feel free to ask, 'What can you do?' and I'll help you out!")
    tutorial_list.append(f"If you need help at any point, just ask 'What can you do?' " \
                         f"and I'll be more than happy to assist you! ")

    if phase == Task.TaskPhase.DOMAIN:
        tutorial_list.append(f"If you don't know what to search for, just say 'home improvement' or 'cooking' "
                             f"and I can guide you to a result! ")
        tutorial_list.append(f"You can tell me what you would like help with and ask me questions. ")

    elif phase == Task.TaskPhase.PLANNING:
        if task_title != '':
            PROMPT_1 = f"This is the summary of {task_title}. If you want to continue, "\
                       f"just say 'start'. You can go back to the search results by saying 'cancel'. "
            PROMPT_2 = f'What do you think of {task_title}? If you want to start, just say ' \
                       f'"start". By saying "restart", you can start a new search. '
            PROMPT_3 = f"You are currently previewing {task_title}. " \
                       f"If you want to continue this task, just say 'start' or go back to the search results " \
                       f"by saying 'cancel'. "
            tutorial_list.extend([PROMPT_1, PROMPT_2, PROMPT_3])
        else:
            TUTORIAL1 = 'You can start a new search by saying "cancel" or "restart".'

            TUTORIAL2_UI = 'You can select one of the results by saying its name, ' \
                           ' or clicking the image on the screen.'
            TUTORIAL2_HL = 'You can select one of the results by saying ' \
                           'the name of the result'

            if headless:
                current_options = "The options are: "
                results_page = task_selection.results_page
                candidates = task_selection.candidates
                candidates_speech_text = populate_choices(candidates[results_page:results_page + 3])
                tutorial_list = [f'{current_options}{candidates_speech_text}{TUTORIAL1} ',
                                 f'{current_options}{candidates_speech_text}{TUTORIAL2_HL} ']
            else:
                tutorial_list = [TUTORIAL1, TUTORIAL2_UI]

    elif phase == Task.TaskPhase.VALIDATING:
        if headless:
            tutorial_list.append('You can navigate through the requirements by saying next or previous, or say '
                                 'cancel to go back to the search results. ')
        else:
            PROMPT_1 = f'You can see what you need for {task_title} on the screen.'\
                       f' Say "start" if you want to see the steps, "cancel" if you would like to go'\
                       f' back to the search results. '
            PROMPT_2 = f'Would you like to continue with {task_title}? If yes, say '\
                       f'"start" to get started, else say "restart" to go back to the search results. '
            tutorial_list.extend([PROMPT_1, PROMPT_2])

    elif phase == Task.TaskPhase.EXECUTING:
        TUTORIAL1 = 'You can navigate through the steps by saying "Next", "Previous" or "Repeat", ' \
                    'or you can go back to the search results by saying "cancel". '

        TUTORIAL2 = 'You can ask any question about the requirements and steps if you have any doubts. ' \
                    'I can also repeat the last instruction if you say Repeat. '

        TUTORIAL4_SCREEN = 'You can say "more details" to see more information about the step, if ' \
                           'available. By saying "show requirements" you can see the things you need again. '

        if headless:
            tutorial_list.extend([f'You are currently doing {task_title}. {TUTORIAL1}',
                                  f'You are currently doing {task_title}. {TUTORIAL2}'])
        else:
            tutorial_list.extend([TUTORIAL1, TUTORIAL2, TUTORIAL4_SCREEN])

    return tutorial_list


def get_recommendations(candidates: List[TaskMap], domain: Session.Domain):
    """Generate recommendation based on TaskMaps metadata.

    Given a list of TaskMaps, this method generates a string with a
    reccomentation based on the TaskMaps' metadata, namely the duration
    and rating of the tasks. The returned recommendation string is then
    attached to the speech_text string in the populate_choices() method.

    Args:
        candidates (List[TaskMap]): a list of TaskMap objects

    Returns:
        Recommendation_string: A string containing the recommendation
        based on duration or rating. If neither is available, a random
        option is suggested.
    """
    preference = ["My personal favourite is option ", "My top pick would be option ", "I would recommend option ",
                  "I would choose option ", "I prefer option ", "I would go with option "]
    preference_questions = ["Why don't we go with option ", "Would you like option ", "Why not try option "]
    preference_rating = [
        [f"{random.choice(preference)}", ". It received the highest rating and I think you could like it! "],
        [f"{random.choice(preference)}", ". It has the best rating! "], \
        ["I really enjoy option ", " and clearly others do too! "],
        ["Option ", " is quite popular among other users. "],
        [f"{random.choice(preference_questions)}", "? The reviews are very good! "]]
    preference_time = ["if you are short on time, go for number", "if you are in a rush, choose option", \
                       "if you're pressed for time, try option "]
    preference_duration = [[f"{random.choice(preference)}", " because it is the quickest. "],
                           [f"{random.choice(preference)}", " because it does not take a lot of time. "], \
                           [f"{random.choice(preference)}",
                            " because it is done quickly and you can enjoy it sooner! "]]
    preference_random_cooking = [[f"{random.choice(preference)}",
                                  ". It is known for its exceptional flavors. I think you'll really enjoy it! "], \
                                 [f"{random.choice(preference)}", ". It looks really tasty! "],
                                 [f"{random.choice(preference_questions)}", "? It looks really tasty!"],
                                 ["Option ", "has a great blend of flavours. Why not try that one? Yum!"]]
    preference_random_diy = [
        [f"{random.choice(preference)}", " because it’s good for both beginners and experienced DIYers! "],
        [f"{random.choice(preference)}", " because you need less specialised tools"], \
        [f"{random.choice(preference_questions)}", "? It seems to be what you are looking for!"]]

    metadata = {}
    for idx, candidate in enumerate(candidates[:3]):
        if candidate.task is not None:
            metadata[idx] = {"rating": candidate.task.rating_out_100, "duration": candidate.task.total_time_minutes,
                            "tags": candidate.task.tags}

    ratings = [metadata[i]["rating"] for i in metadata if metadata[i]["rating"] is not None]
    durations = [metadata[i]["duration"] for i in metadata if metadata[i]["duration"] is not None]

    max_rating_index = None
    if ratings:
        max_rating_index = max(metadata, key=lambda i: metadata[i]["rating"])
        if len(ratings) == 1:
            max_rating_index = next(iter(metadata))

    min_duration_index = None
    if durations:
        min_duration_index = min(metadata, key=lambda i: metadata[i]["duration"])
        if len(durations) == 1:
            min_duration_index = next(iter(metadata))

    rating_prompt = random.choice(preference_rating)
    if min_duration_index:
        time_prompt = f" However, {random.choice(preference_time)} {min_duration_index + 1} . "
    else:
        time_prompt = f" However, {random.choice(preference_time)} 1 . "
    duration_prompt = random.choice(preference_duration)
    random_prompt_cooking = random.choice(preference_random_cooking)
    random_prompt_diy = random.choice(preference_random_diy)

    recommendation_string = ""

    if max_rating_index is not None:
        recommendation_string = f"{rating_prompt[0]} {max_rating_index + 1}{rating_prompt[1]}"
        if min_duration_index is not None and max_rating_index != min_duration_index:
            recommendation_string += f"{time_prompt}"
    elif min_duration_index is not None:
        recommendation_string = f"{duration_prompt[0]} {min_duration_index + 1}{duration_prompt[1]}"
    else:
        if domain == Session.Domain.COOKING:
            recommendation_string = f"{random_prompt_cooking[0]} {random.randint(1, 3)}{random_prompt_cooking[1]}"
        if domain == Session.Domain.DIY:
            recommendation_string = f"{random_prompt_diy[0]} {random.randint(1, 3)}{random_prompt_diy[1]}"

    max_rating = candidates[max_rating_index] if max_rating_index is not None else None
    min_duration = candidates[min_duration_index] if min_duration_index is not None else None
    if recommendation_string == "":
        recommendation_string = "I don't have a recommendation. "

    return recommendation_string, max_rating, min_duration


def should_trigger_theme(user_utterance, theme_word):
    caller = getframeinfo(stack()[1][0])
    logger.info("should_trigger_theme called from %s:%d" % (caller.filename, caller.lineno))

    if theme_word == "":
        logger.info('Theme word is empty')
        return False, ""

    if user_utterance.lower() == theme_word.lower():
        logger.info(f'THEME TRIGGERED due to {theme_word} in {user_utterance}')
        return True, theme_word
    
    similarity = jaccard_sim(theme_word.lower(), user_utterance.lower())
    if similarity > 0.8:
        logger.info(f'THEME TRIGGERED due to Jaccard Similarity {similarity} > 0.8 of {theme_word} and {user_utterance}')
        return True, theme_word
    
    logger.info(f"Similarity between {theme_word} and {user_utterance}: {round(similarity,2)}")
        
    logger.info('No theme found in user utterance')
    return False, ""
