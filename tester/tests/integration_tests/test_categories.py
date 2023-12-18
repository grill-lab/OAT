from constant_answers import DETAIL_PAGE
from utils import (
    INTRO_PROMPTS, INTRODUCE_CATEGORY, CATEGORY_RESULTS, SUGGESTED_THEME_DAY, SUGGESTED_THEME_DAY_COUNTDOWN,
    SUGGESTED_THEME_WEEK, CATEGORY_PROMPT
)


def test_categories_selection(new_session_obj, interaction_obj):
    session = new_session_obj
    session['headless'] = False

    # greeting
    response = interaction_obj.run("hello", session)
    full_theme_prompts = []
    full_theme_prompts.extend(SUGGESTED_THEME_WEEK)
    full_theme_prompts.extend(SUGGESTED_THEME_DAY)
    full_theme_prompts.extend(SUGGESTED_THEME_DAY_COUNTDOWN)
    theme_prompts = [prompt.split('{0}')[1].split("{")[0] for prompt in full_theme_prompts]
    theme_prompts.extend(INTRO_PROMPTS)
    interaction_obj.check_prompts(response, theme_prompts)

    # querying for a task (category)
    response = interaction_obj.run("apples", session)
    cat_prompts = [prompt.split('{0}')[0] for prompt in CATEGORY_PROMPT]
    interaction_obj.check_prompts(response, cat_prompts)

    # selecting a subcategory
    response = interaction_obj.run("the 3rd 1", session)
    prompts = [prompt.split('{0}')[1].split('{1}')[0] for prompt in INTRODUCE_CATEGORY]
    interaction_obj.check_prompts(response, prompts)

    # selecting a subcategory
    response = interaction_obj.run("the 3rd 1", session)
    interaction_obj.check_prompts(response, [p.split('{0}')[0] for p in CATEGORY_RESULTS])
    output_text1 = interaction_obj.get_speech_text(response)

    # go back to subcategory selection
    response = interaction_obj.run("back", session)
    interaction_obj.check_prompts(response, [p.strip() for p in INTRO_PROMPTS])

    # querying for a task (category)
    response = interaction_obj.run("apples", session)
    cat_prompts = [prompt.split('{0}')[0] for prompt in CATEGORY_PROMPT]
    interaction_obj.check_prompts(response, cat_prompts)

    # selecting a subcategory
    response = interaction_obj.run("the 3rd 1", session)
    prompts = [prompt.split('{0}')[1].split('{1}')[0] for prompt in INTRODUCE_CATEGORY]
    interaction_obj.check_prompts(response, prompts)

    # selecting a subcategory
    response = interaction_obj.run("the 3rd 1", session)
    interaction_obj.check_prompts(response, [p.split('{0}')[0] for p in CATEGORY_RESULTS])
    output_text1 = interaction_obj.get_speech_text(response)

    # selecting a task (1) -> moving to validation
    response = interaction_obj.run("yes", session)
    interaction_obj.check_prompts(response, [DETAIL_PAGE])