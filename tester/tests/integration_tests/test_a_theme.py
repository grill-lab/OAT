from utils import (
    SUGGESTED_THEME_DAY_COUNTDOWN, SUGGESTED_THEME_DAY, INTRO_PROMPTS, SUGGESTED_THEME_WEEK, logger
)

from constant_answers import (
    SAFETY_WARNING, WANT_TO_START
)


def test_not_current_theme(new_session_obj, interaction_obj):
    session = new_session_obj
    session['headless'] = True

    response = interaction_obj.run("hello", session)
    full_theme_prompts = []
    full_theme_prompts.extend(SUGGESTED_THEME_WEEK)
    full_theme_prompts.extend(SUGGESTED_THEME_DAY)
    full_theme_prompts.extend(SUGGESTED_THEME_DAY_COUNTDOWN)
    theme_prompts = [prompt.split('{0}')[1].split("{")[0] for prompt in full_theme_prompts]
    INTRO_PROMPTS.extend(theme_prompts)
    interaction_obj.check_prompts(response, INTRO_PROMPTS)

    speech_text = interaction_obj.get_speech_text(response)
    matched_theme_snippet = ""
    for i in range(len(theme_prompts)):
        if theme_prompts[i] in speech_text:
            matched_theme_snippet = full_theme_prompts[i]

    theme = ""

    if matched_theme_snippet != "":
        prefix = matched_theme_snippet.split("{")[0]
        after = matched_theme_snippet.split("}")[1].split("{")[0]
        without_pre = speech_text.split(prefix)[1]
        theme = without_pre.split(after)[0]

    if "apple" in theme.lower():
        print('Skipping test since apple is current theme')
    else:
        
        logger.info(theme)
        logger.info("theme")
        
        response = interaction_obj.run(theme, session)
        theme_results_yes = interaction_obj.get_speech_text(response)
        first_yes_res = theme_results_yes.split(': ')[1].split(' by')[0]

        if first_yes_res in ["Gluten-Free Apple Walnut Pancakes", "Whole Grain Apple Waffles", "Rustic Apple Galette"]:
            assert False, "We return a theme that is not currently active!"
        else:
            return True


def test_theme(new_session_obj, interaction_obj):
    session = new_session_obj
    session['headless'] = True

    response = interaction_obj.run("hello", session)
    full_theme_prompts = []
    full_theme_prompts.extend(SUGGESTED_THEME_WEEK)
    full_theme_prompts.extend(SUGGESTED_THEME_DAY)
    full_theme_prompts.extend(SUGGESTED_THEME_DAY_COUNTDOWN)
    theme_prompts = [prompt.split('{0}')[1].split("{")[0] for prompt in full_theme_prompts]
    INTRO_PROMPTS.extend(theme_prompts)
    interaction_obj.check_prompts(response, INTRO_PROMPTS)

    speech_text = interaction_obj.get_speech_text(response)
    matched_theme_snippet = ""
    for i in range(len(theme_prompts)):
        if theme_prompts[i] in speech_text:
            matched_theme_snippet = full_theme_prompts[i]

    theme = ""

    if matched_theme_snippet != "":
        prefix = matched_theme_snippet.split("{")[0]
        after = matched_theme_snippet.split("}")[1].split("{")[0]
        without_pre = speech_text.split(prefix)[1]
        theme = without_pre.split(after)[0]

    if theme != "":
        # select theme by saying yes
        response = interaction_obj.run(theme, session)
        theme_results_yes = interaction_obj.get_speech_text(response)
        first_yes_res = theme_results_yes.split(': ')[1].split(' by')[0]

        # select a result
        response = interaction_obj.run(first_yes_res, session)
        selected_first_yes = interaction_obj.get_speech_text(response)

        # go back to selection
        response = interaction_obj.run('go back', session)
        selection_response = interaction_obj.get_speech_text(response)
        assert first_yes_res in selection_response

        # go back to domain
        response = interaction_obj.run('restart', session)
        interaction_obj.check_prompts(response, INTRO_PROMPTS)

        response = interaction_obj.run('the third one', session)
        selected_third = interaction_obj.get_speech_text(response)
        if not ": " in selected_third:
            third_first_res = selected_third
        else:
            third_first_res = selected_third.split(': ')[1].split(' by')[0]
        assert third_first_res == first_yes_res

        # go back to domain
        response = interaction_obj.run('restart', session)
        interaction_obj.check_prompts(response, INTRO_PROMPTS)

        # select theme by asking for theme
        back_to_theme_response = interaction_obj.run(theme, session)
        speech_text_back_theme = interaction_obj.get_speech_text(back_to_theme_response)
        if not ": " in speech_text_back_theme:
            back_first_res = speech_text_back_theme
        else:
            back_first_res = speech_text_back_theme.split(': ')[1].split(' by')[0]

        assert first_yes_res == back_first_res

        # select the first result
        response = interaction_obj.run(back_first_res, session)
        selected_first_name = interaction_obj.get_speech_text(response)

        assert selected_first_name == selected_first_yes

        # 'do you want to see the ingredients?'
        response = interaction_obj.run("yes", session)

        # warning text + read through the requirements
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

    else:
        assert False, "There is currently no active theme"
