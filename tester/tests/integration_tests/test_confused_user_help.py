from constant_answers import SAFETY_WARNING, VALIDATION_HELP, SEARCH_RESULTS_HEADLESS, \
    EXECUTION_HELP, WANT_TO_START, PLANNING_HELP

from utils import INTRO_PROMPTS, SUGGESTED_THEME_WEEK, SUGGESTED_THEME_DAY, SUGGESTED_THEME_DAY_COUNTDOWN


def has_joke(speech_text):
    if "something funny" in speech_text:
        return True
    else:
        return False


def test_confused_user(new_session_obj, interaction_obj):
    session = new_session_obj
    session['headless'] = True

    response = interaction_obj.run("hello", session)
    theme_prompts = [prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_WEEK]
    theme_prompts.extend([prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_DAY])
    theme_prompts.extend([prompt.split('{0}')[0] for prompt in SUGGESTED_THEME_DAY_COUNTDOWN])
    INTRO_PROMPTS.extend(theme_prompts)
    interaction_obj.check_prompts(response, INTRO_PROMPTS)

    # querying for a task
    response = interaction_obj.run("I want to make strawberry cheesecake", session)
    interaction_obj.check_prompts(response, SEARCH_RESULTS_HEADLESS)

    # response = interaction_obj.run("I am confused", session)
    # interaction_obj.check_prompts(response, ["You can"])

    response = interaction_obj.run("the second one", session)
    interaction_obj.check_prompts(response, ["by"])
    interaction_obj.check_prompts(response, ["ingredients"])

    response = interaction_obj.run("help me", session)
    interaction_obj.check_prompts(response, PLANNING_HELP, 1)

    # detail page in headless - do you want to see the requirements
    response = interaction_obj.run("yes", session)
    interaction_obj.check_prompts(response, ["ingredients"])

    response = interaction_obj.run("help me", session)
    interaction_obj.check_prompts(response, VALIDATION_HELP, 1)

    # 32. warning text
    # read through the requirements
    turns = 0
    while SAFETY_WARNING not in interaction_obj.get_speech_text(response) and turns < 10:
        response = interaction_obj.run("I am so confused can you help me", session)
        interaction_obj.check_prompts(response, VALIDATION_HELP, 1)

        response = interaction_obj.run("next", session)
        turns += 1

    interaction_obj.check_prompts(response, [SAFETY_WARNING])
    interaction_obj.check_prompts(response, [WANT_TO_START])

    response = interaction_obj.run("help me I am confused", session)
    assert not interaction_obj.is_closed(response)
    interaction_obj.check_prompts(response, VALIDATION_HELP, 1)

    # validation step - 'do you want to start?'
    response = interaction_obj.run("yes", session)
    # starting recipe
    output_text = interaction_obj.get_speech_text(response)
    assert "Step 1" in output_text

    if has_joke(output_text):
        response = interaction_obj.run('no', session)

    response = interaction_obj.run("I am confused", session)
    interaction_obj.check_prompts(response, EXECUTION_HELP, 1)

    # go forward a step
    response = interaction_obj.run("next", session)
    # step 2
    next_output_text = interaction_obj.get_speech_text(response)
    if has_joke(next_output_text):
        response = interaction_obj.run('no', session)
        next_output_text = interaction_obj.get_speech_text(response)
    assert output_text != next_output_text
    assert "Step 2" in next_output_text

    response = interaction_obj.run("help me please", session)
    interaction_obj.check_prompts(response, EXECUTION_HELP, 1)
