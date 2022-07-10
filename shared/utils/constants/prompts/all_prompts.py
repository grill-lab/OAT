########################
# DOMAIN PHASE PROMPTS #
########################

DANGEROUS_TASK_RESPONSES = [
    "Actually, I can't help you with potentially dangerous tasks, bye!",
]

LEVEL_ONE_MEDICAL_RESPONSES = [
    "Sorry I can't give medical advice",
]

LEVEL_TWO_MEDICAL_RESPONSES = [
    "I really can't give you any medical advice",
]

LEVEL_ONE_FINANCIAL_RESPONSES = [
    "Sorry I can't give financial advice",
]

LEVEL_TWO_FINANCIAL_RESPONSES = [
    "I really can't give you any financial advice",
]

LEVEL_ONE_LEGAL_RESPONSES = [
    "Sorry I can't give legal advice",
]

LEVEL_TWO_LEGAL_RESPONSES = [
    "I really can't give you any legal advice",
]

INTRO_PROMPTS = [
    "I'm good at cooking and home improvement. What do you need?",
]

LEVEL_ONE_UNDEFINED_DOMAIN_RESPONSES = [
    "I'm good at walking you through a recipe or a home project. What can I help you with?",
]

LEVEL_TWO_UNDEFINED_DOMAIN_RESPONSES = [
    "I can help you with a task if you say something like: 'How do I cook a pizza?'. What do feel like doing?",
]

##########################
# PLANNING PHASE PROMPTS #
##########################

MORE_RESULTS_FALLBACK = [
    "I'm sorry but I don't have any more results for you. "
]

MORE_RESULTS_INTRO = [
    "These are some other options I found. ",

]

PREVIOUS_RESULTS_INTRO = [
    'Here are the previous results. ',
]

ALL_RESULTS_PROMPT = [
    "That's all I've got. You can say cancel to search for something else.  ",
]

FIRST_RESULT_SET_PROMPT = [
    "This is the first page of results. ",
]

OUT_OF_RANGE_COREF_RESPONSE = [
    "You can only pick one of the options I mentioned. Which would you like? ",
]

NO_PLANNING = [
                "Okay, thanks,. What do you want to do? ",
            ]

YES_PLANNING = [
                "Thanks, ",
            ]

SELECT_POSSIBILITY = [
    "Select one of the results by saying the name of the result. ",
]

FEEDBACK_PLANNING = [
                'Do you like the suggested matches? ',
            ]

###########################
# EXECUTION PHASE PROMPTS #
###########################

EXECUTION_NO_CANCEL = [
    "We can't cancel a task that's already in progress just now."
]

###################
# GENERAL PROMPTS #
###################

RIND_FALLBACK_RESPONSE = [
    "Gosh, I had trouble understanding that."
]

UNSAFE_BOT_RESPONSE = [
    "I'm sorry, I had an internal problem, can we keep going?",
]

###################
# FAREWELL PROMPTS #
###################

COOKING_FAREWELL = f"Great job, you finished your task! "


###################
# ASR ERR PROMPTS #
###################

ASR_ERROR = [
    "'{}' sounded like a an error"
]

#####################
# CHIT-CHAT PROMPTS #
#####################

CHIT_CHAT = [
    "That's pretty neat! Let's keep going!"
]