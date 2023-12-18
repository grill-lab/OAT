from constant_answers import WANT_TO_START, SAFETY_WARNING, \
    DETAIL_PAGE_DIY, NO_DETAILS_AVAILABLE, REQUIREMENTS_INFO, NO_REQ_FOUND, \
    GO_BACK_TO_TASK, PREFERENCE_ELICITATION_DIY_1, SEARCH_RESULTS, SEARCH_RESULTS_HEADLESS

from utils import INTRO_PROMPTS, PAUSING_PROMPTS, SUGGESTED_THEME_WEEK, SUGGESTED_THEME_DAY, SUGGESTED_THEME_DAY_COUNTDOWN


def if_joke_then_reject(speech_text, interaction_obj, session):
    joke_prompt = " This reminds me of something funny"
    if joke_prompt in speech_text:
        # interaction_obj.run("no", session)
        return speech_text.split(joke_prompt)[0]
    else:
        return speech_text


def test_details_ingredients_pause_screen(new_session_obj, interaction_obj):
    session = new_session_obj
    session['headless'] = False

    response = interaction_obj.run("hello", session)
    theme_prompts = [prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_WEEK]
    theme_prompts.extend([prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_DAY])
    theme_prompts.extend([prompt.split('{0}')[0] for prompt in SUGGESTED_THEME_DAY_COUNTDOWN])
    INTRO_PROMPTS.extend(theme_prompts)
    interaction_obj.check_prompts(response, INTRO_PROMPTS)

    # querying for a task
    response = interaction_obj.run("DIY", session)
    interaction_obj.check_prompts(response, PREFERENCE_ELICITATION_DIY_1)

    response = interaction_obj.run("I want to paint a wall", session)
    interaction_obj.check_prompts(response, SEARCH_RESULTS)

    response = interaction_obj.run("number one", session)
    interaction_obj.check_prompts(response, DETAIL_PAGE_DIY)

    # 'do you want to see the ingredients?'
    response = interaction_obj.run("yes", session)
    interaction_obj.check_prompts(response, [SAFETY_WARNING])
    interaction_obj.check_prompts(response, [WANT_TO_START])

    # validation step - 'do you want to start?'
    response = interaction_obj.run("yes", session)
    # starting recipe - step 1
    output_text = interaction_obj.get_speech_text(response)

    if "multiple methods" in output_text:
        # select first method
        response = interaction_obj.run("yes", session)
        output_text = interaction_obj.get_speech_text

    # go forward a step
    response = interaction_obj.run("next", session)
    # step 2
    next_output_text = interaction_obj.get_speech_text(response)
    next_output_text = if_joke_then_reject(next_output_text, interaction_obj, session)
    assert "Step 2" in next_output_text
    assert output_text != next_output_text

    # go forward a step
    response = interaction_obj.run("next", session)
    # step 3
    next_next_output_text = interaction_obj.get_speech_text(response)
    next_next_output_text = if_joke_then_reject(next_next_output_text, interaction_obj, session)
    assert "Step 3" in next_next_output_text
    assert next_next_output_text != next_output_text

    # go back a step
    response = interaction_obj.run("previous", session)
    # step 2
    previous_output_text = interaction_obj.get_speech_text(response)
    previous_output_text = if_joke_then_reject(previous_output_text, interaction_obj, session)
    assert "Step 2" in previous_output_text
    assert previous_output_text == next_output_text

    # pausing
    # conversation ID: 400f5857a2c0127492d80a18d
    response = interaction_obj.run("pause", session)
    interaction_obj.check_prompts(response, PAUSING_PROMPTS)

    # invoking and continuing conversation
    response = interaction_obj.run("next", session)
    restart_output_text = interaction_obj.get_speech_text(response)
    restart_output_text = if_joke_then_reject(restart_output_text, interaction_obj, session)
    assert next_next_output_text == restart_output_text

    # go back a step
    response = interaction_obj.run("go back", session)
    # step 2
    previous_output_text = interaction_obj.get_speech_text(response)
    previous_output_text = if_joke_then_reject(previous_output_text, interaction_obj, session)
    assert "Step 2" in previous_output_text
    assert previous_output_text == next_output_text

    # ask for details
    response = interaction_obj.run("show me more details", session)
    details_output_text = interaction_obj.get_speech_text(response)
    assert details_output_text != next_next_output_text and \
           ((len(details_output_text) > len(previous_output_text)) or (NO_DETAILS_AVAILABLE in details_output_text))

    # go next in task
    response = interaction_obj.run("go next", session)
    continue_task = interaction_obj.get_speech_text(response)
    continue_task = if_joke_then_reject(continue_task, interaction_obj, session)
    assert continue_task == next_next_output_text

    # ask for requirements
    response = interaction_obj.run("show me the requirements", session)
    output_text = interaction_obj.get_speech_text(response)
    assert (REQUIREMENTS_INFO in output_text) or (NO_REQ_FOUND in output_text)
    assert GO_BACK_TO_TASK in output_text

    # go back to task
    response = interaction_obj.run("go back", session)
    output_text = interaction_obj.get_speech_text(response)
    output_text = if_joke_then_reject(output_text, interaction_obj, session)
    assert output_text in continue_task
    assert continue_task == output_text

    # response = interaction_obj.run("No never mind stop", session)
    # assert interaction_obj.is_closed(response)


def test_details_ingredients_headless(new_session_obj, interaction_obj):
    session = new_session_obj
    session['headless'] = True

    # greeting
    response = interaction_obj.run("hi", session)
    theme_prompts = [prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_WEEK]
    theme_prompts.extend([prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_DAY])
    theme_prompts.extend([prompt.split('{0}')[0] for prompt in SUGGESTED_THEME_DAY_COUNTDOWN])
    INTRO_PROMPTS.extend(theme_prompts)
    interaction_obj.check_prompts(response, INTRO_PROMPTS)

    # `eggs in clouds` produces ASR error
    response = interaction_obj.run("eggs benedict", session)
    interaction_obj.check_prompts(response, SEARCH_RESULTS_HEADLESS)

    response = interaction_obj.run("the first one", session)
    interaction_obj.check_prompts(response, ["by"])
    interaction_obj.check_prompts(response, ["ingredients"])

    # 'do you want to see the ingredients?'
    response = interaction_obj.run("yes", session)

    # 32. warning text
    # read through the requirements
    turns = 0
    while SAFETY_WARNING not in interaction_obj.get_speech_text(response) and turns < 10:
        response = interaction_obj.run("next", session)
        turns += 1
    interaction_obj.check_prompts(response, [SAFETY_WARNING])
    interaction_obj.check_prompts(response, [WANT_TO_START])

    # validation step - 'do you want to start?'
    response = interaction_obj.run("yes", session)
    # starting recipe
    output_text = interaction_obj.get_speech_text(response)
    assert "Step 1" in output_text

    if "multiple methods" in output_text:
        # select first method
        response = interaction_obj.run("yes", session)
        output_text = interaction_obj.get_speech_text(response)
        # are you ready to get started?
        response = interaction_obj.run("yes", session)
    else:
        # go forward a step
        response = interaction_obj.run("next", session)

    # step 2
    next_output_text = interaction_obj.get_speech_text(response)

    if "multiple methods" in next_output_text:
        # select first method
        response = interaction_obj.run("yes", session)
        next_output_text = interaction_obj.get_speech_text(response)

    next_output_text = if_joke_then_reject(next_output_text, interaction_obj, session)

    assert output_text != next_output_text
    assert "Step 2" in next_output_text

    # go forward a step
    response = interaction_obj.run("next", session)
    # step 3
    next_next_output_text = interaction_obj.get_speech_text(response)
    next_next_output_text = if_joke_then_reject(next_next_output_text, interaction_obj, session)
    assert next_next_output_text != next_output_text
    assert "Step 3" in next_next_output_text

    # go back a step
    response = interaction_obj.run("previous", session)
    # step 2
    previous_output_text = interaction_obj.get_speech_text(response)
    previous_output_text = if_joke_then_reject(previous_output_text, interaction_obj, session)
    assert next_output_text in previous_output_text
    assert "Step 2" in previous_output_text

    # ask for details
    response = interaction_obj.run("show me more details", session)
    details_output_text = interaction_obj.get_speech_text(response)
    assert details_output_text != next_next_output_text and \
           ((len(details_output_text) > len(previous_output_text)) or (NO_DETAILS_AVAILABLE in details_output_text))

    # go next in task
    response = interaction_obj.run("go next", session)
    continue_task = interaction_obj.get_speech_text(response)
    continue_task = if_joke_then_reject(continue_task, interaction_obj, session)
    assert next_next_output_text in continue_task
    assert "Step 3" in continue_task

    # ask for requirements
    response = interaction_obj.run("show me the requirements", session)
    output_text = interaction_obj.get_speech_text(response)
    assert ("you need" in output_text) or (NO_REQ_FOUND in output_text)
    assert GO_BACK_TO_TASK in output_text

    # go back to task
    response = interaction_obj.run("go back", session)
    output_text = interaction_obj.get_speech_text(response)
    output_text = if_joke_then_reject(output_text, interaction_obj, session)
    assert continue_task in output_text
    assert "Step 3" in output_text

    # OBJECT SHOULD CLOSE
    # end conversation
    # response = interaction_obj.run("let's stop this", session)
    # assert interaction_obj.is_closed(response)
