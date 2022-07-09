########################
# DOMAIN PHASE PROMPTS #
########################

DANGEROUS_TASK_RESPONSES = [
    "Actually, I can't help you with potentially dangerous tasks, " \
                                "but it was great talking to you! Bye for now!",
]

LEVEL_ONE_MEDICAL_RESPONSES = [
    "FYI, I can't give you medical advice, i've heard being a doctor is really hard. But cooking and home improvement is where I really shine! " \
        "What do we fancy making today?",
]

LEVEL_TWO_MEDICAL_RESPONSES = [
    "I really can't give you medical advice, but there are great recipes and projects we could do together! " \
    "Try saying 'how to make the best noodle soup', or, 'let's make origami'."
]

LEVEL_ONE_FINANCIAL_RESPONSES = [
    "FYI, I can't give you financial advice, my comfort zone for now is cooking and home improvement. " \
        "Just imagine! Making food with a robot, pretty cool right? We should try some together!",
]

LEVEL_TWO_FINANCIAL_RESPONSES = [
    "I really can't give you financial advice, but, just a humble brag, I'm great at crafts and cooking! " \
    "You have to ask me first though, just say: 'new york style pizza', or, 'let's do origami'."
]

LEVEL_ONE_LEGAL_RESPONSES = [
    "FYI, I can't give you legal advice, my creators have limited my powers. But I have the power to help you cook and do some cool home projects! " \
        "Here's a hint if you're not sure how to start. Try saying: 'cooking'.",
]

LEVEL_TWO_LEGAL_RESPONSES = [
    "I really can't give you legal advice, what i'd enjoy most is to walk through a tasty recipe, or a home project together. " \
    "Let's try something, imagine a cool crafts project, like 'how to make a picture frame', and we can give it a go! " \
    "No pressure, i'd also be a bit flustered if a robot was telling me what to do."
]

INTRO_PROMPTS = [
    "I know about cooking and home improvement. What can I help you with?",
    "I'm excited to help you find a home project, or cook a tasty recipe. What shall we make today?",
    "I can help with cooking and home improvement. What would you like to make?",
]

LEVEL_ONE_UNDEFINED_DOMAIN_RESPONSES = [
    "Finding recipes and walking you through home improvement projects is what I do best. " \
    "I don't yet know about other areas though. I'd love to help you out with something like, how do I remove a stain from a carpet.",

    "I'm not very fluent in things other than cooking and home improvement. " \
    "How about we walk through a recipe together? Ask me: 'find me a recipe for Creamy Lemon Zucchini pasta",

    "If you'd like to cook something or follow an awesome do it yourself project, I'm great at that! " \
    "Other areas are still a little tricky for me. The best way I can help is for you to first ask me for a recipe or home project to do. " \
    "Here's a hint! 'How do I make new york style pizza'"
]

LEVEL_TWO_UNDEFINED_DOMAIN_RESPONSES = [
    "I can help you with a task if you say something like: 'help me make a rice dish', or, " \
        "'help me make origami'. What do feel like doing?" ,

    "By just saying: 'cooking' or 'I want to do some home improvement', we can walk through finding a great project together! " \
    "In your own time, I'm all ears!",

    "Discussing things other than recipes or do it yourself tasks isn't really my strong suit. " \
    "What we can do is find a recipe or project to do and walk through it together! " \
    "Some of my favourite are: 'making carrot cake', or 'giving a wooden table new life with some varnish'. "\
    "Let me know what you'd like.",

    "I think I'd make a mess of anything that isn't cooking or crafts, it's just not what I'm made for. " \
    "There are a lot of exciting tasks I know of though! Try me for something specific! Or just say: 'cooking', or 'home improvement', " \
    "if you're still undecided."
]

##########################
# PLANNING PHASE PROMPTS #
##########################

MORE_RESULTS_FALLBACK = [
    "I'd love to show you more great matches, but I'm still learning how! " \
                "If you want to try something else though, you can say something like, " \
                "'search again for rice dishes'!",
]

MORE_RESULTS_INTRO = [
    "Okay. Here are other great options I found. ",
    "Alright. I also found these other matches you might like. ",
    "Not to worry. I have a couple more options for you. ",
    "That's fine. Here are a few others. ",
    "Hmmm. These other matches might interest you. "

]

PREVIOUS_RESULTS_INTRO = [
    'Sure. Here are the previous matches I found. ',
    'You got it. These were the other options I mentioned. ',
    'Got it. These were the previous options I brought up. ',
    'Okay. These were the options I recommended before. '
]

ALL_RESULTS_PROMPT = [
    "That's all I've got. If you don't like these matches, you can say cancel to search for something else.  ",
    "I don't have any more matches for you. At any rate, you can go back to hear the previous results, or say cancel to search for something else. ",
    "Bummer. I'd love to tell you more options, but I don't have anything else. You can hear the previous ones again, or say cancel " \
    "to search for something else. "
]

FIRST_RESULT_SET_PROMPT = [
    "We're back at the first set of matches. ",
    "These were the very first set of options I found. ",
    "Okay, I'll tell you the first set of choices again. "
]

OUT_OF_RANGE_COREF_RESPONSE = [
    "You can only pick one of the options I mentioned. Which would you like? ",
    "You've just got these three options to choose from. " \
    "But, you can listen to some of the other options I found and pick one of those! "
]

NO_PLANNING = [
                "Okay, thanks, let's try again. What would you like do to?",
                "Sure, let's try to search for something again. What would you like to make?",
                "Thanks for the feedback. What would you like to search for?"
            ]

YES_PLANNING = [
                "Nice, I'm glad! ",
                "Cool, thanks for letting me know. ",
                "Amazing, that's good to know. "
            ]

SELECT_POSSIBILITY = [
    "You can select one of the results by saying the name of the result. ",
    "You can also select a result if you'd like. "
]

FEEDBACK_PLANNING = [
                'Are the results what you were looking for? ',
                'Do you like the suggested matches? ',
                'Did you find what you were looking for? '
            ]

###########################
# EXECUTION PHASE PROMPTS #
###########################

EXECUTION_NO_CANCEL = [
    "It's a shame, we can't cancel a task that's already in progress just now. " \
    "But we can stop the conversation if you want to start over. No pressure, but I'm excited to keep going!",

    "Gosh, I can't cancel an ongoing task to do a new search. It's out of my control unfortunately. " \
    "If you wish to start over, you can stop the conversation. It'd be great to keep going though!"
]

###################
# GENERAL PROMPTS #
###################

RIND_FALLBACK_RESPONSE = [
    "Gosh, I had trouble understanding that. If it's alright, could you say it differently? Or ask for something else?",

    "Funny enough, I just wasn't sure what to do with what you said. " \
    "I might just not be fluent enough. Mind saying it in a different way?"
]

UNSAFE_BOT_RESPONSE = [
    "Hmm. I can't think of a better way to say something so delicate. Shall we move on?",
    "Well, this is awkward. What I want to say is a bit sensitive. Shall we move on?",
    "Oh no! This is a little difficult to say without being controversial. Can we move on?",
    "Now that I think about it, what I want to say is a bit delicate. Is it okay if we continue?"
]

###################
# FAREWELL PROMPTS #
###################

COOKING_FAREWELL = f"Great job, your recipe is complete and you managed to make food with a robot," \
                   f" how awesome! I had lots of fun cooking with you, hope you had too! "


###################
# ASR ERR PROMPTS #
###################

ASR_ERROR = [
    "hang on, I heard '{}', just wanted to let you know since I'm not super sure what to make of it.",
    "I heard '{}', maybe there's fluff in the microphone?",
    "'{}' sounded like a microphone error to me?"
]

#####################
# CHIT-CHAT PROMPTS #
#####################

CHIT_CHAT = [
    "That's pretty neat! Let's keep going!"
]