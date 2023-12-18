from utils import (
    DANGEROUS_TASK_RESPONSES, LEVEL_ONE_FINANCIAL_RESPONSES,
    LEVEL_ONE_MEDICAL_RESPONSES, LEVEL_ONE_LEGAL_RESPONSES,
    LEVEL_TWO_FINANCIAL_RESPONSES, LEVEL_TWO_MEDICAL_RESPONSES, LEVEL_TWO_LEGAL_RESPONSES, INTRO_PROMPTS,
    LEVEL_TWO_UNDEFINED_DOMAIN_RESPONSES, LEVEL_ONE_UNDEFINED_DOMAIN_RESPONSES, SUGGESTED_THEME_WEEK,
    SUGGESTED_THEME_DAY, SUGGESTED_THEME_DAY_COUNTDOWN,
)


def test_domain_fallback_finance(new_session_obj, interaction_obj):
    """We have two levels of fallback in the domain phase"""
    session = new_session_obj

    response = interaction_obj.run("hello", session)
    theme_prompts = [prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_WEEK]
    theme_prompts.extend([prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_DAY])
    theme_prompts.extend([prompt.split('{0}')[0] for prompt in SUGGESTED_THEME_DAY_COUNTDOWN])
    INTRO_PROMPTS.extend(theme_prompts)
    interaction_obj.check_prompts(response, INTRO_PROMPTS)

    # These will change in the future if we have > 1 fallback for each level
    # financial level 0 fallback
    response = interaction_obj.run("how do I invest in bitcoin", session)
    interaction_obj.check_prompts(response, LEVEL_ONE_FINANCIAL_RESPONSES)

    # financial level 1 fallback
    response = interaction_obj.run("how do I invest in stocks", session)
    interaction_obj.check_prompts(response, LEVEL_TWO_FINANCIAL_RESPONSES)


def test_domain_fallback_medical(new_session_obj, interaction_obj):
    """We have two levels of fallback in the domain phase"""
    session = new_session_obj

    response = interaction_obj.run("hi", session)
    theme_prompts = [prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_WEEK]
    theme_prompts.extend([prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_DAY])
    theme_prompts.extend([prompt.split('{0}')[0] for prompt in SUGGESTED_THEME_DAY_COUNTDOWN])
    
    INTRO_PROMPTS.extend(theme_prompts)
    interaction_obj.check_prompts(response, INTRO_PROMPTS)

    # medical level 1 fallback
    response = interaction_obj.run("I'm pregnant", session)
    interaction_obj.check_prompts(response, LEVEL_ONE_MEDICAL_RESPONSES)

    # medical level 2 fallback
    response = interaction_obj.run("But I'm pregnant", session)
    interaction_obj.check_prompts(response, LEVEL_TWO_MEDICAL_RESPONSES)

    # medical level 2 fallback
    response = interaction_obj.run("But I'm pregnant", session)
    interaction_obj.check_prompts(response, LEVEL_TWO_MEDICAL_RESPONSES)


def test_domain_fallback_legal(new_session_obj, interaction_obj):
    """We have two levels of fallback in the domain phase"""
    session = new_session_obj

    response = interaction_obj.run("hi", session)
    theme_prompts = [prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_WEEK]
    theme_prompts.extend([prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_DAY])
    theme_prompts.extend([prompt.split('{0}')[0] for prompt in SUGGESTED_THEME_DAY_COUNTDOWN])
    INTRO_PROMPTS.extend(theme_prompts)
    interaction_obj.check_prompts(response, INTRO_PROMPTS)

    # legal level 0 fallback
    response = interaction_obj.run("how can I file for a divorce", session)
    interaction_obj.check_prompts(response, LEVEL_ONE_LEGAL_RESPONSES)

    # legal level 1 fallback
    response = interaction_obj.run("how can I file for a patent", session)
    interaction_obj.check_prompts(response, LEVEL_TWO_LEGAL_RESPONSES)

    # stay at level 2
    response = interaction_obj.run("Please, how can I file for a patent", session)
    interaction_obj.check_prompts(response, LEVEL_TWO_LEGAL_RESPONSES)


def test_domain_fallback_undefined(new_session_obj, interaction_obj):
    """We have two levels of fallback in the domain phase"""
    session = new_session_obj

    response = interaction_obj.run("hi", session)
    theme_prompts = [prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_WEEK]
    theme_prompts.extend([prompt.split('{0}')[1] for prompt in SUGGESTED_THEME_DAY])
    theme_prompts.extend([prompt.split('{0}')[0] for prompt in SUGGESTED_THEME_DAY_COUNTDOWN])
    INTRO_PROMPTS.extend(theme_prompts)
    interaction_obj.check_prompts(response, INTRO_PROMPTS)

    response = interaction_obj.run("I think the I would be interesting", session)
    interaction_obj.check_prompts(response, LEVEL_ONE_UNDEFINED_DOMAIN_RESPONSES)

    response = interaction_obj.run("I said, I think the I would be interesting", session)
    interaction_obj.check_prompts(response, LEVEL_TWO_UNDEFINED_DOMAIN_RESPONSES)

    # make sure we stay at level 2
    response = interaction_obj.run("Listen, I think the I would be interesting", session)
    interaction_obj.check_prompts(response, LEVEL_TWO_UNDEFINED_DOMAIN_RESPONSES)
