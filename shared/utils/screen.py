import random
import json

from taskmap_pb2 import OutputInteraction, ScreenInteraction, Image, Session, Task, ExtraInfo
from theme_pb2 import ThemeResults

from datetime import datetime

from utils import (
    set_source, logger, repeat_screen_response, is_in_user_interaction
)

from .constants.global_variables.joke_trigger_words import JOKE_TRIGGER_WORDS
from .constants.prompts import CONTINUE_PROMPTS


def build_chat_screen(policy_output: OutputInteraction, session: Session, user_utterance: str) -> OutputInteraction:
    logger.info("building the chat screen")
    screen: ScreenInteraction = ScreenInteraction()
    screen.format = ScreenInteraction.ScreenFormat.TEXT_ONLY
    screen.paragraphs.append(f'{policy_output.speech_text}')
    screen.hint_text = random.choice(["Continue", "what can you do"])
    screen.on_click_list.append("repeat")

    if not session.headless and len(session.turn) > 1 and session.task.taskmap.title != "":
        if session.task.phase == Task.TaskPhase.EXECUTING:
            logger.info(session.turn[-2].agent_response.interaction)
            step_images = session.turn[-2].agent_response.interaction.screen.image_list
            if len(step_images) > 0:
                background = session.turn[-2].agent_response.interaction.screen.image_list[0].path
            else:
                background = session.task.taskmap.thumbnail_url
        else:
            background = session.task.taskmap.thumbnail_url
    else:
        background = "https://oat-2-data.s3.amazonaws.com/images/background.jpg"

    screen.background = background

    policy_output.screen.ParseFromString(screen.SerializeToString())
    set_source(policy_output)
    return policy_output


def build_help_grid_screen(session: Session, theme_result=None) -> OutputInteraction:
    logger.info('Building help corner')
    base_path = "https://oat-2-data.s3.amazonaws.com/images"
    help_options_image = {
        "next": f"{base_path}/help_next.png",
        "back": f"{base_path}/help_back.png",
        "search": f"{base_path}/help_search.png",
        "question": f"{base_path}/help_qa.png",
        "restart": f"{base_path}/help_restart.png",
        "repeat": f"{base_path}/help_repeat.png",
        "previous": f"{base_path}/help_previous.png",
        "More details": f"{base_path}/more_details_2.png",
        "ingredients": f"{base_path}/help_show1.png",
        "tools": f"{base_path}/help_show2.png",
        "start": f"{base_path}/help_start.png",
        "select": f"{base_path}/help_select.png",
        "substitutions": f"{base_path}/substitution.png",
        "compare results": f"{base_path}/compare.png",
        "facts": f"{base_path}/facts.png",
        "finder": f"{base_path}/finder.png",
        "jokes": f"{base_path}/jokes.png",
        "video": f"{base_path}/video.png",
        "theme": f"{base_path}/idea.png",
        "preferences": f"{base_path}/preferences.png",
    }
    if theme_result is not None:
        theme_title = theme_result.theme_word if theme_result.theme_word != "current_recommendation" \
            else theme_result.description
    else:
        theme_title = ""

    different_hint_texts = {
        "search": "search for pasta recipes",
        "More details": "tell me more details",
        "ingredients": "show me the ingredients",
        "tools": "show me what I need",
        "select": "select the first one",
        "substitution": "can I substitute milk with oat milk",
        "compare results": "which one do you recommend",
        "facts": "tell me a fun fact",
        "jokes": "tell me a joke",
        "video": "play the video",
        "theme": theme_title,
        "preferences": "find me a vegan recipe"
    }

    help_options = get_helpful_options(session, theme_result)
    output: OutputInteraction = OutputInteraction()
    screen: ScreenInteraction = ScreenInteraction()
    screen.format = ScreenInteraction.ScreenFormat.GRID_LIST
    screen.headline = "Help corner"

    for keyword, prompt in help_options.items():
        image: Image = Image()
        image.path = help_options_image.get(keyword, "https://oat-2-data.s3.amazonaws.com/images/multi_domain_default.jpg")
        image.title = keyword
        image.alt_text = prompt
        image.description = different_hint_texts.get(keyword, "")
        screen.image_list.append(image)
        screen.on_click_list.append(f'{keyword}_button')

    screen.on_click_list.append("repeat")

    screen.hint_text = "Go back"

    output.screen.MergeFrom(screen)

    speech_options = [
        "Let me show you what I can do. Click one of the buttons to hear an explanation of " \
        "what your current options are. Say 'Go back' or press the back button in the top left corner at any time to " \
        "resume your conversation. ",
        "Welcome to the help corner. All the buttons you can see describe what I am currently able to do. "
        "If you press the back button in the top left corner, you can leave the help corner and resume "
        "your conversation. "
    ]

    output.speech_text = random.choice(speech_options)

    return output


def build_farewell_screen(theme_result: ThemeResults, session: Session) -> ScreenInteraction:
    screen: ScreenInteraction = ScreenInteraction()
    screen.format = ScreenInteraction.ScreenFormat.FAREWELL

    screen.headline = "Well done!"
    screen.paragraphs.append(f"You just completed: {session.task.taskmap.title}")
    screen.paragraphs.append(f"Continue with our current recommendations: ")
    image: Image = screen.image_list.add()
    # image.path = session.task.taskmap.thumbnail_url
    if session.domain == Session.Domain.COOKING:
        image_options = [
            "https://oat-2-data.s3.amazonaws.com/images/gifs/baking_cat.gif",
            # "https://oat-2-data.s3.amazonaws.com/images/gifs/kid_eating.gif"
        ]
    else:
        image_options = [
            "https://oat-2-data.s3.amazonaws.com/images/gifs/drawing_cat.gif"
        ]
    image.path = random.choice(image_options)

    screen.buttons.append(theme_result.theme_word)
    screen.on_click_list.append(theme_result.theme_word.lower())

    screen.buttons.append("More ideas")
    screen.on_click_list.append("search again")

    screen.hint_text = random.choice(["exit", theme_result.theme_word])

    return screen


def get_helpful_options(session, theme_result=None):

    domain = session.domain
    phase = session.task.phase
    task_title = session.task.taskmap.title
    in_farewell = session.task.state.in_farewell

    prompts = {}
    task_type = "task" if session.domain != Session.Domain.COOKING else "recipe"

    if phase == Task.TaskPhase.DOMAIN:
        # search for, questions, restart, repeat
            
        if theme_result is not None and theme_result.date:
            theme_date = datetime.strptime(theme_result.date, "%d-%m-%Y")
            now_date = datetime.today()
            days = theme_date - now_date
            if days.days == 0:
                when = "today"
            elif days.days > 1:
                when = f"in {days.days} days"
            else:
                when = "tomorrow"
            prompts["theme"] = f"Did you know that it's {theme_result.theme_word} {when}? How about we celebrate " \
                               f"together? Say {theme_result.theme_word} to select our recommendations. "
        else:
            prompts["theme"] = f"Every day, we have daily recommendations for you! Those recipes are " \
                               f"some of our favourites, so I would definitely check them out. "

        prompts["search"] = "What would you like to search for? If you don't know, just say 'home improvement' " \
                            "or 'cooking' and I can guide you to a result! "
        prompts["restart"] = "If you say restart at any time of our conversation, I will start over. "
        prompts["repeat"] = "Say repeat to make me repeat what I last said in other words. "

    elif phase == Task.TaskPhase.PLANNING:
        if task_title != '':
            # we are on summary page
            if session.task_selection.theme.theme != "":
                prompts["theme"] = f"You have currently selected our {session.task_selection.theme.theme} theme, and " \
                                   f"you have currently selected one of the recommended tasks, {task_title}. " \
                                   f" Continue if you want to try the {task_type} we curated for you. "

            if domain == Session.Domain.COOKING:
                prompts["ingredients"] = f'We are currently on the summary of {task_title}. ' \
                                          f'By saying "show ingredients" you can see the ingredients you will need. '
            else:
                prompts["tools"] = f'We are currently on the summary of {task_title}. ' \
                                    f'By saying "show tools" you can see the tools and equipment you will need. '

            prompts["More details"] = f"You can ask me anything about the task you selected, which is called " \
                                      f"{task_title}. For example, ask me how long it will take or " \
                                      f"ask for substitutions. "

            prompts["search"] = "You can start a new search by saying, for example, 'search for pasta" \
                                " recipes'. "
            prompts["restart"] = 'By saying "restart", we start the conversation over. '

        else:
            has_category = any([cand.HasField('category') for cand in session.task_selection.candidates_union])

            if theme_result is not None and session.task_selection.theme.theme == "" and theme_result.date:
                theme_date = datetime.strptime(theme_result.date, "%d-%m-%Y")
                now_date = datetime.today()
                days = theme_date - now_date
                if days.days == 0:
                    when = "today"
                elif days.days > 1:
                    when = f"in {days.days} days"
                else:
                    when = "tomorrow"
                prompts["theme"] = f"Did you know that it's {theme_result.theme_word} {when}? How about we celebrate " \
                                   f"together? Say {theme_result.theme_word} to select our recommendations. "
            else:
                prompts["theme"] = f"Every day, we have daily recommendations for you! Those {task_type}s are " \
                                   f"some of our favourites, so I would definitely check them out. "

            if session.task_selection.elicitation_turns > 0 and session.task_selection.preferences_elicited is False:
                # we are in elicitation
                domain = "cooking" if session.domain == Session.Domain.COOKING else "home improvement"
                prompts["preferences"] = f"Thanks for telling me that you want to do some {domain} today! If you tell " \
                                         f"me more about your preferences, I will hopefully be able to find you " \
                                         f"something cool to do! "
            else:
                prompts["compare results"] = "I can compare the results for you, if you need further assistance on which " \
                                             f"{task_type} to select. Say, which one do you recommend! "

            if session.task_selection.theme.theme != "":
                prompts["theme"] = f"You have currently selected our {session.task_selection.theme.theme} theme." \
                                   f" Nice work! Celebrate with us by trying one of the {task_type}s we curated for " \
                                   f"you. Select one of the options by saying its name. "

            # still on image list - options are seen
            if has_category:
                prompts["finder"] = f"I think that your previous search was a bit vague. This means " \
                                    f"I have prepared a {task_type} finder for you to help me find a better " \
                                    f"result for you. Try it out by selecting the third option" \
                                    f" or saying {task_type} finder! "

            prompts["search"] = "You can search for cooking, home improvement and crafting tasks. " \
                                "To search say for example, 'search for pasta recipes'. "

    elif phase == Task.TaskPhase.VALIDATING:

        prompts["search"] = "You can start a new search for a task by saying, for example, 'search for pasta" \
                            " recipes'. "
        prompts["More details"] = f"If you would like to know more about {task_title}, ask me anything! "

        if domain == Session.Domain.COOKING:
            prompts["ingredients"] = f'Ask me anything about the ingredients needed for {task_title}. ' \
                                    f'For example, I can assist you in replacing ingredients ' \
                                     f'and adjusting the recipe for you. '
        else:
            prompts["tools"] = f'Ask me anything about the tools needed for {task_title}. ' \
                               f'Ask any question you might have, and I will try my best to help you! '

    elif phase == Task.TaskPhase.EXECUTING and not in_farewell:

        prompts["More details"] = 'You can say "more details" to see more information about the step. '
        description = session.turn[-1].agent_response.interaction.description
        if description != "":
            prompts["More details"] += 'This step has more details, so why not try it out? '
        else:
            prompts["More details"] += "This step does not have more details, but I'll let you know " \
                                       "in future when I know more! "
        prompts["search"] = "You can always start a new search for a task by saying, for example, 'search for pasta" \
                            " recipes'. "
        if session.domain == Session.Domain.COOKING:
            prompts["substitutions"] = f"You can ask me anything about substitutions for the recipe's ingredients. "

        prompts["facts"] = f"I often know fun facts about what we are working on. If you interested, stay tuned! "
        prompts["jokes"] = f"I am trying my best to be funny. Say 'tell me a joke' if you would like to hear one! "

        video = session.turn[-1].agent_response.interaction.screen.video
        prompts["video"] = "I can also play videos, but I am not able to search for them yet. "
        if video.title != "":
            prompts["video"] += "This step has a video that describes it! You can check it out by saying play video. "
        else:
            has_general_video = len([step.response.screen.video.title for step in session.task.taskmap.steps
                                     if step.response.screen.video.title != ""]) > 0
            if has_general_video:
                prompts["video"] += "This task has a video, so stay tuned! "
            else:
                prompts["video"] += "This task does not have a video, but my creators are actively working on " \
                                    "getting more videos for you in future! "

        # if domain == Session.Domain.COOKING:
        #     prompts["ingredients"] = "By saying 'show requirements' you can see the ingredients you need again. " \
        #                              "You can ask me anything about the recipe's ingredients, and I'll " \
        #                              "try to look up an answer for you!"
        # else:
        #     prompts["tools"] = 'By saying "show requirements" you can see the tools and equipment you need again. '

    elif in_farewell == True:
        # search, restart, previous
        prompts["search"] = "You can start a new search for a task by saying, for example, 'search for pasta" \
                            " recipes'. "
        prompts["restart"] = 'By saying "restart", you can start a new search.'
        prompts["previous"] = f"Say previous to go back to the last step of {task_title}. "

    return prompts


def build_default_screen(output_interaction: OutputInteraction) -> OutputInteraction:
    logger.info('Building default screen')
    
    with open('/shared/utils/curated_jokes_images.json', 'r') as f:
        jokes = json.load(f)

    joke_intro_fact = [
        "Sorry to interrupt, but I want to share something funny with you! Have you ever noticed that ",
        "I just thought of something funny that I had to share with you. Have you ever noticed that ",
        "Quick pause, I just thought of something funny if you don't mind. Have you ever noticed that ",
        "A bit unrelated, but I just realised something. Did you know that ",
        "Here is a fact I just realised. Did you know that ",
    ]

    joke_joke_intro = [
        "I know we are in the middle of something, but I just thought of something funny. ",
        "Sorry to interrupt, but I just learned this joke today and had to share it with you. ",
        "Can we pause real quick, I just thought of something funny. "
    ]

    joke = random.choice(jokes)

    if joke.get('type') == "fact":
        output_interaction.speech_text = random.choice(joke_intro_fact)
    else:
        output_interaction.speech_text = random.choice(joke_joke_intro)

    extra_info: ExtraInfo = ExtraInfo()
    extra_info.keyword = joke['keyword']
    extra_info.text = joke['joke']
    extra_info.image_url = joke.get('image', '')
    default_images = [
        "https://oat-2-data.s3.amazonaws.com/images/gifs/dancing_robot.gif",
    ]
    image_url = extra_info.image_url if extra_info.image_url != "" else random.choice(default_images)
    compile_joke_screen(extra_info, image_url=image_url, output=output_interaction)

    output_interaction.speech_text += extra_info.text

    output_interaction.speech_text += random.choice(CONTINUE_PROMPTS)

    return output_interaction


def compile_joke_screen(extra_info, image_url, output) -> OutputInteraction:
    screen: ScreenInteraction = ScreenInteraction()

    if extra_info.keyword != "":
        screen.footer = f"A joke about {extra_info.keyword}"
    else:
        screen.footer = f"A joke for you"

    screen.format = ScreenInteraction.ScreenFormat.TEXT_IMAGE
    screen.headline = extra_info.text
    extra_info_image: Image = Image()
    extra_info_image.path = image_url
    screen.image_list.append(extra_info_image)
    output.screen.MergeFrom(screen)


def build_joke_screen(session, extra_info) -> OutputInteraction:
    output: OutputInteraction = OutputInteraction()
    speech_text = extra_info.text
    output.speech_text = speech_text

    image_url = ""
    if extra_info.image_url != "" and not session.headless:
        image_url = extra_info.image_url
    elif len(session.turn) > 1:
        if is_in_user_interaction(user_interaction=session.turn[-2].user_request.interaction,
                                  utterances_list=JOKE_TRIGGER_WORDS) and not session.headless \
                and session.turn[-2].agent_response.interaction.screen.format in [
            ScreenInteraction.ScreenFormat.TEXT_IMAGE, ScreenInteraction.ScreenFormat.TEXT_ONLY
        ]:
            image_url = "https://oat-2-data.s3.amazonaws.com/images/gifs/dancing_robot.gif"

    if image_url != "":
        compile_joke_screen(extra_info, image_url, output)
    else:
        output = repeat_screen_response(session, output)

    return output
