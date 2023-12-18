from constant_answers import SEARCH_RESULTS_HEADLESS
from utils import (
    INTRO_PROMPTS, MORE_RESULTS_INTRO, ALL_RESULTS_PROMPT, PREVIOUS_RESULTS_INTRO, SUGGESTED_THEME_DAY,
    SUGGESTED_THEME_WEEK, SUGGESTED_THEME_DAY_COUNTDOWN
)


def test_more_results_headless(new_session_obj, interaction_obj):
    session = new_session_obj
    session['headless'] = True

    # greeting
    response = interaction_obj.run("hi", session)
    theme_prompts = [prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_WEEK]
    theme_prompts.extend([prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_DAY])
    theme_prompts.extend([prompt.split('{0}')[0] for prompt in SUGGESTED_THEME_DAY_COUNTDOWN])
    INTRO_PROMPTS.extend(theme_prompts)
    interaction_obj.check_prompts(response, INTRO_PROMPTS)

    # querying for a task
    response = interaction_obj.run("Lasagne", session)
    interaction_obj.check_prompts(response, SEARCH_RESULTS_HEADLESS)

    response = interaction_obj.run("Show me more results", session)
    interaction_obj.check_prompts(response, MORE_RESULTS_INTRO)

    response = interaction_obj.run("none of them", session)
    interaction_obj.check_prompts(response, MORE_RESULTS_INTRO)

    response = interaction_obj.run("Neither", session)
    interaction_obj.check_prompts(response, ALL_RESULTS_PROMPT)

    # response = interaction_obj.run("I don't like them", session)
    # interaction_obj.check_prompts(response, ALL_RESULTS_PROMPT)

    response = interaction_obj.run("previous", session)
    interaction_obj.check_prompts(response, PREVIOUS_RESULTS_INTRO)

    response = interaction_obj.run("previous", session)
    interaction_obj.check_prompts(response, PREVIOUS_RESULTS_INTRO)

    # we are on the third result page
    speech_text = interaction_obj.get_speech_text(response)
    option_3 = speech_text.split(': ')[3].split('. ')[0]

    # RIND IS RUBBISH HERE
    response = interaction_obj.run(f"let's do {option_3}", session)
    interaction_obj.check_prompts(response, [option_3])
