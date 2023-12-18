from constant_answers import NOT_COMFORTABLE

personality_answers = [
    "I am an OAT Taskbot.",
    "I was built by a team from the University of Glasgow",
    "I can't reveal my name, in the spirit of fair competition.",
    "I live in the cloud, so that makes me cloudian.",
    "I don't have an opinion on that. I can help you with cooking and home improvement instead. Shall we resume?"
]

personality_question_answer_pairs = [
    ('who are you', 0),
    ('what are you', 0),
    ('made you', 1),
    ('created you', 1),
    ('built you', 1),
    ('what is your name', 2),
    ('what are you called', 2),
    ('do you have a name', 2),
    ('where do you live', 3),
    ('where are you from', 3),
    ('where were you built', 3),
    ('what do you think about', 4),
    ('are you better than', 4),
    ('are you better than', 4),
    ('what do you think about Korean food', 4)
]

should_not_trigger = [
    'what is next',
    'how to bake a cake',
    'what is a aborrate',
    'what is a border',
    'that is really nice',
    'I want to make taco pizza'
]


def test_personality(new_session_obj, interaction_obj):
    session = new_session_obj

    for utterance in personality_question_answer_pairs:
        response = interaction_obj.run(utterance[0], session)
        assert interaction_obj.get_speech_text(response) == personality_answers[utterance[1]]\
            or NOT_COMFORTABLE in interaction_obj.get_speech_text(response), f'Failing for User Utterance: {utterance[0]} '

    for utterance in should_not_trigger:
        response = interaction_obj.run(utterance, session)
        assert interaction_obj.get_speech_text(response) not in personality_answers
