from constant_answers import THEME_SEARCH, SEARCH_RESULTS_HEADLESS, DETAIL_PAGE_HEADLESS

from utils import (
    INTRO_PROMPTS, SUGGESTED_THEME_WEEK, SUGGESTED_THEME_DAY, SUGGESTED_THEME_DAY_COUNTDOWN,
    MORE_RESULTS_INTRO
)


def test_planning_question(new_session_obj, interaction_obj):
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
    response = interaction_obj.run("Pizza", session)
    interaction_obj.check_prompts(response, THEME_SEARCH + [SEARCH_RESULTS_HEADLESS])

    # more results
    response = interaction_obj.run("None", session)
    interaction_obj.check_prompts(response, MORE_RESULTS_INTRO)

    # actually no cancel
    response = interaction_obj.run("can we start over", session)
    interaction_obj.check_prompts(response, INTRO_PROMPTS)

    response = interaction_obj.run("Pizza with mushrooms", session)
    interaction_obj.check_prompts(response, SEARCH_RESULTS_HEADLESS)

    response = interaction_obj.run("No", session)
    speech_text = interaction_obj.get_speech_text(response)
    assert any([prompt.strip() in speech_text for prompt in INTRO_PROMPTS])

    response = interaction_obj.run("maybe something with chili and sweetcorn", session)
    interaction_obj.check_prompts(response, SEARCH_RESULTS_HEADLESS)

    response = interaction_obj.run("the first one", session)
    interaction_obj.check_prompts(response, [DETAIL_PAGE_HEADLESS])

    # response = interaction_obj.run("I want to search again", session)
    # # goes into vague search - elicitation process
    # # is that the behaviour we want?? Should be more like cancel behaviour, no?
    # assert any(prompt in get_speech_text(response) for prompt in PREFERENCE_ELICITATION_COOKING_2) or \
    #        any(prompt in get_speech_text(response) for prompt in PREFERENCE_ELICITATION_COOKING_1)
    #
