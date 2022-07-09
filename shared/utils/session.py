from typing import List
import random


def get_star_string(rating_float, rating_count):
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


def format_author(author):
    if "," in author:
        return author.split(",")[0]
    else:
        name_parts = author.split(' ')
        if len(name_parts) > 3:
            return "".join([f'{a[0].capitalize()}' for a in name_parts if a != ''])
        else:
            abbrev = [f'{a[0]}.' for a in name_parts if a != ''][:-1]
            abbrev.append(name_parts[-1])

            if len(" ".join(abbrev)) > 15:
                abbrev = [f'{a[0]}.' for a in name_parts if a != '']
            return " ".join(abbrev)


def format_author_headless(author):
    if "," in author:
        return author.split(",")[0]
    else:
        return author


def get_credit_from_url(url):
    """ Given a URL return a website name or [UNKNOWN] token."""
    from urllib.parse import urlparse

    domain = urlparse(url).netloc
    if domain:
        website_keyword = domain.split('.')
        if len(website_keyword) > 2:
            website_name = website_keyword[1:-1][0]
        else:
            website_name = domain
        return website_name
    return ''


def get_credit_from_taskmap(taskmap) -> str:
    """ Build string to provide credit for original taskmap content. """
    source_url = taskmap.source_url
    if source_url:
        website_name = get_credit_from_url(source_url)
        return website_name
    # If no source url -> check thumbnail url as a proxy.
    else:
        image_url = taskmap.thumbnail_url
        if image_url:
            website_name = get_credit_from_url(image_url)
            return website_name
    return ''


def close_session(session, output):
    from taskmap_pb2 import SessionState

    session.state = SessionState.CLOSED
    session.greetings = False  # To greet the user next time
    output.close_interaction = True
    session.task.state.validation_options_displayed = False
    session.task.state.validation_page = 0

    return session, output


def is_in_user_interaction(user_interaction, *,
                           intents_list: List[str] = [],
                           utterances_list: List[str] = []):
    user_intents = user_interaction.intents
    user_utterance = user_interaction.text

    matched_intents = set.intersection(set(user_intents), set(intents_list))
    return user_utterance in utterances_list or len(matched_intents) != 0


def repeat_screen_response(session, response):
    if not session.headless and len(session.turn) > 1:
        response.screen.ParseFromString(session.turn[-2].agent_response.interaction.screen.SerializeToString())

    return response


def format_requirements(req_list):
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


def screen_summary_taskmap(taskmap, speech_req):
    from taskmap_pb2 import ScreenInteraction, Image

    screen: ScreenInteraction = ScreenInteraction()
    screen.headline = taskmap.title
    screen.format = ScreenInteraction.ScreenFormat.TEXT_IMAGE

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
        screen.paragraphs.append(f"<b>Rating:</b> {get_star_string(rating, taskmap.rating_count)}")

    if taskmap.difficulty is not None and taskmap.difficulty != "":
        screen.paragraphs.append(f"<b>Difficulty:</b> {taskmap.difficulty}")

    if taskmap.active_time_minutes != 0:
        screen.paragraphs.append(f"<b>Active time:</b> "
                                 f"{convert_minutes_to_hours(taskmap.active_time_minutes)}")
    if taskmap.total_time_minutes != 0:
        screen.paragraphs.append(f"<b>Total time:</b> "
                                 f"{convert_minutes_to_hours(taskmap.total_time_minutes)}")

    if taskmap.serves != '' and taskmap.serves is not None and taskmap.serves != "None":
        screen.paragraphs.append(f"<b>Serves:</b> {taskmap.serves}")

    if len(taskmap.requirement_list) > 0:
        screen.paragraphs.append(f"<b>Requires:</b> {len(taskmap.requirement_list)} {speech_req}")

    if len(taskmap.steps) > 0:
        screen.paragraphs.append(f"<b>Number of steps:</b> {len(taskmap.steps)}")

    if taskmap.description != '':
        if len(taskmap.description) < 150:
            screen.paragraphs.append(f"<b>Description:</b> {taskmap.description}")
    elif taskmap.voice_summary != '':
        screen.paragraphs.append(f"<b>Description:</b> {taskmap.voice_summary}")

    return screen


def headless_task_summary(taskmap, speech_req):
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


def show_ingredients_screen(session, requirements_list, response):
    from taskmap_pb2 import ScreenInteraction, Image, OutputInteraction

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

    else:
        output: OutputInteraction = repeat_screen_response(session, response)

    return output


def display_screen_results(candidates, output) -> List:
    from taskmap_pb2 import ScreenInteraction, Image

    # output.screen.headline = f'"{session.task_selection.theme.theme}". Say "cancel" to go back.'
    output.screen.format = ScreenInteraction.ScreenFormat.IMAGE_CAROUSEL

    on_click_list = []
    for idx, candidate in enumerate(candidates):
        image: Image = output.screen.image_list.add()
        image.path = candidate.thumbnail_url
        image.title = candidate.title

        if candidate.author is not None and candidate.author != "":
            image.description = f"By {format_author(candidate.author)}"
        elif candidate.domain_name is not None and candidate.domain_name != "":
            image.description = f"By {candidate.domain_name}"
        else:
            image.title = candidate.title

        if candidate.rating_out_100 is not None and candidate.rating_out_100 != 0 \
                and candidate.rating_count is not None:
            rating = candidate.rating_out_100 / 20
            image.alt_text = f'({candidate.rating_count})'
            image.ratingValue = rating
        on_click_list.append(str(idx+1))
    
    return on_click_list


def populate_choices(candidates) -> str:
    from taskmap_pb2 import TaskMap

    speech_text = ''
    idx: int
    candidate: TaskMap
    ordinal_phrases = [
        ["The first one is", "The second is", "And, finally"],
        ["First is", "Second is", "And, third"]
    ]
    ordinals = random.choice(ordinal_phrases)
    for idx, candidate in enumerate(candidates[:3]):
        result = f"{candidate.title}"
        if candidate.author is not None and candidate.author != "":
            result += f" by {format_author_headless(candidate.author)}"
        elif candidate.domain_name is not None and candidate.domain_name != "":
            result += f" by {candidate.domain_name}"
        speech_text += f'{ordinals[idx]}: {result}. '
    return speech_text


def build_video_button(output, video):
    import random
    from taskmap_pb2 import ScreenInteraction

    VIDEO_SUGGESTIONS = [
        '. I have found a video that might be relevant.',
        '. How about a video:',
        '. Maybe this video will help:',
        ". By the way, I've got a useful video for you:",
        '. Why not checkout this video I found:'
    ]

    screen = ScreenInteraction()
    screen.ParseFromString(output.screen.SerializeToString())
    speech_text = ""

    if video.title != "":
        speech_text = f"{random.sample(VIDEO_SUGGESTIONS, 1)[0]} {video.title}?"
        if 0 < len(screen.buttons) < 1:
            temp = screen.buttons[0]
            screen.buttons.append(temp)

        screen.buttons[0] = 'Video'
        screen.on_click_list[0] = 'play video'

        if len(screen.buttons) == 1:
            screen.buttons.append('Next')
            screen.on_click_list.append('Next')

        screen.hint_text = 'play video'

    return speech_text, screen


def filter_speech_text(speech_text):
    import re

    replace_regexes = [(r'((\d)+).?F', r'\1ºF')]
    for find_reg, replace_with in replace_regexes:
        speech_text = re.sub(find_reg, replace_with, speech_text)

    speech_text = speech_text.replace(" degrees F.", "ºF.")
    return speech_text


