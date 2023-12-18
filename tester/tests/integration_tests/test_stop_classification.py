from constant_answers import PREFERENCE_ELICITATION_COOKING_1, SEARCH_RESULTS_HEADLESS
from utils import (
    INTRO_PROMPTS, SUGGESTED_THEME_DAY, SUGGESTED_THEME_WEEK, SUGGESTED_THEME_DAY_COUNTDOWN
)


def test_stop_intent(new_session_obj, interaction_obj):
    session = new_session_obj
    session['headless'] = True

    response = interaction_obj.run("hello", session)
    theme_prompts = [prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_WEEK]
    theme_prompts.extend([prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_DAY])
    theme_prompts.extend([prompt.split('{0}')[0] for prompt in SUGGESTED_THEME_DAY_COUNTDOWN])
    INTRO_PROMPTS.extend(theme_prompts)
    interaction_obj.check_prompts(response, INTRO_PROMPTS)

    # querying for a task
    response = interaction_obj.run("cooking", session)
    interaction_obj.check_prompts(response, PREFERENCE_ELICITATION_COOKING_1)

    # extracting preferences
    response = interaction_obj.run("I love chicken casserole", session)
    interaction_obj.check_prompts(response, SEARCH_RESULTS_HEADLESS)

    # response = interaction_obj.run("Chicken is my favorite food", session)
    # interaction_obj.check_prompts(response, SEARCH_RESULTS)

    response = interaction_obj.run("second", session)
    interaction_obj.check_prompts(response, ["by"])

    response = interaction_obj.run("no never mind stop", session)
    # assert interaction_obj.is_closed(response) is True
