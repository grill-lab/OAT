from constant_answers import WANT_TO_START, SAFETY_WARNING, DETAIL_PAGE_HEADLESS, \
    DETAIL_PAGE, WANT_TO_START_REPROMPT, THEME_SEARCH, SEARCH_RESULTS, SEARCH_RESULTS_HEADLESS, REQS_ENUMERATION, \
    DETAIL_PAGE_HEADLESS

from utils import INTRO_PROMPTS, SUGGESTED_THEME_WEEK, SUGGESTED_THEME_DAY, SUGGESTED_THEME_DAY_COUNTDOWN


def test_reading_ingredients_screen(new_session_obj, interaction_obj):
    session = new_session_obj
    session['headless'] = False

    # greeting
    response = interaction_obj.run("hi", session)
    theme_prompts = [prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_WEEK]
    theme_prompts.extend([prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_DAY])
    theme_prompts.extend([prompt.split('{0}')[0] for prompt in SUGGESTED_THEME_DAY_COUNTDOWN])
    INTRO_PROMPTS.extend(theme_prompts)
    interaction_obj.check_prompts(response, INTRO_PROMPTS)

    # querying for a task
    response = interaction_obj.run("Pizza", session)
    interaction_obj.check_prompts(response, SEARCH_RESULTS)

    # let’s make the first one
    response = interaction_obj.run("the first one", session)
    interaction_obj.check_prompts(response, DETAIL_PAGE)

    # 'do you want to see the ingredients?'
    response = interaction_obj.run("yes", session)

    # 32. warning text
    interaction_obj.check_prompts(response, [SAFETY_WARNING])
    interaction_obj.check_prompts(response, [WANT_TO_START])

    # select reading through all the requirements 'button'
    response = interaction_obj.run("show the ingredients", session)
    interaction_obj.check_prompts(response, ["You need"])

    # validation step - 'do you want to start?'
    response = interaction_obj.run("yes", session)
    # starting recipe
    output_text = interaction_obj.get_speech_text(response)
    assert "Step 1" in output_text


def test_skip_requirements_screen(new_session_obj, interaction_obj):
    session = new_session_obj
    session['headless'] = False

    # greeting
    response = interaction_obj.run("hi", session)
    theme_prompts = [prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_WEEK]
    theme_prompts.extend([prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_DAY])
    theme_prompts.extend([prompt.split('{0}')[0] for prompt in SUGGESTED_THEME_DAY_COUNTDOWN])
    INTRO_PROMPTS.extend(theme_prompts)
    interaction_obj.check_prompts(response, INTRO_PROMPTS)

    # querying for a task - should trigger theme search or normal search
    response = interaction_obj.run("I want strawberry cake", session)
    interaction_obj.check_prompts(response, SEARCH_RESULTS)

    # let’s make the first one
    response = interaction_obj.run("the first one", session)
    interaction_obj.check_prompts(response, [DETAIL_PAGE])

    # 'do you want to see the ingredients?'
    response = interaction_obj.run("no", session)
    interaction_obj.check_prompts(response, [WANT_TO_START_REPROMPT])

    # validation step - 'do you want to start?'
    response = interaction_obj.run("yes", session)
    assert "Step 1" in interaction_obj.get_speech_text(response)


def test_show_requirements(new_session_obj, interaction_obj):
    session = new_session_obj
    session['headless'] = True

    # greeting
    response = interaction_obj.run("hi", session)
    theme_prompts = [prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_WEEK]
    theme_prompts.extend([prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_DAY])
    theme_prompts.extend([prompt.split('{0}')[0] for prompt in SUGGESTED_THEME_DAY_COUNTDOWN])
    INTRO_PROMPTS.extend(theme_prompts)
    interaction_obj.check_prompts(response, INTRO_PROMPTS)

    # querying for a task - should trigger theme search or normal search
    response = interaction_obj.run("Meatballs", session)
    prompts = THEME_SEARCH
    prompts.append(SEARCH_RESULTS_HEADLESS)
    interaction_obj.check_prompts(response, prompts)

    # let’s make the first one
    response = interaction_obj.run("the first one", session)
    interaction_obj.check_prompts(response, [DETAIL_PAGE_HEADLESS])

    # 'do you want to hear them?'
    response = interaction_obj.run("yes", session)
    interaction_obj.check_prompts(response, REQS_ENUMERATION)

    # validation step - 'do you want to start?'
    response = interaction_obj.run("start cooking", session)
    assert "Step 1" in interaction_obj.get_speech_text(response)