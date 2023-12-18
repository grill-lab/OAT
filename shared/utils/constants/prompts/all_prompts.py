########################
# DOMAIN PHASE PROMPTS #
########################

DANGEROUS_TASK_RESPONSES = [
    "Actually, I can't help you with potentially dangerous tasks, bye!",
]

LEVEL_ONE_MEDICAL_RESPONSES = [
    "Sorry I can't give medical advice.",
]

LEVEL_TWO_MEDICAL_RESPONSES = [
    "I really can't give you any medical advice.",
]

LEVEL_ONE_FINANCIAL_RESPONSES = [
    "Sorry I can't give financial advice.",
]

LEVEL_TWO_FINANCIAL_RESPONSES = [
    "I really can't give you any financial advice.",
]

LEVEL_ONE_LEGAL_RESPONSES = [
    "Sorry I can't give legal advice.",
]

LEVEL_TWO_LEGAL_RESPONSES = [
    "I really can't give you any legal advice.",
]

INTRO_PROMPTS = [
    "I'm good at cooking and home improvement. What do you need?",
]

LEVEL_ONE_UNDEFINED_DOMAIN_RESPONSES = [
    "I'm good at walking you through a recipe or a home project. What can I help you with?",
]

LEVEL_TWO_UNDEFINED_DOMAIN_RESPONSES = [
    "I can help you with a task if you say something like: 'How do I cook a pizza?'. What do you feel like doing?",
]

SUGGESTED_THEME_WEEK = [
    "It's {0} week! I can help with cooking, home improvement and {0}. Try some of our {0} recommendations by saying {0}.",
]

SUGGESTED_THEME_WEEK_with_examples = [
    "{1} I can help with cooking, home improvement and {2}. Not sure? Say {0} for recommendations.",
]

SUGGESTED_THEME_DAY_COUNTDOWN = [
    "{0} is just {1} away! Take a look at our special recommendations if you're interested. "
    "I'm also here to assist you with any home improvement or cooking tasks. What would you like to do?",
]

SUGGESTED_THEME_DAY = [
    "Today, it's {0}! Are you keen to try out some of our recommendations? Say {0} to check them out. "
]

##########################
# PLANNING PHASE PROMPTS #
##########################

MORE_RESULTS_FALLBACK = ["I'm sorry but I don't have any more results for you. "]

MORE_RESULTS_INTRO = [
    "These are some other options I found.",
]

PREVIOUS_RESULTS_INTRO = [
    "Here are the previous results. ",
]

ALL_RESULTS_PROMPT = [
    "That's all I've got. You can say cancel to search for something else. ",
]

FIRST_RESULT_SET_PROMPT = [
    "This is the first page of results.",
]

OUT_OF_RANGE_COREF_RESPONSE = [
    "You can only pick one of the options I mentioned. Which would you like?",
]

NO_PLANNING = [
    "Okay, thanks,. What do you want to do?",
]

YES_PLANNING = [
    "Thanks, ",
]

SELECT_POSSIBILITY = [
    "Select one of the results by saying the name of the result.",
]

SELECT_QUESTION = ["Which one would you like? "]

FEEDBACK_PLANNING = [
    "Do you like the suggested matches? ",
]

INGREDIENT_FUNNY_REMARK = [
    " Do you want to check if you have all the {0}?",
]

REPLACE_SUGGESTION = [
    "I can try change the recipe to use.",
]

PROMOTE_SUBSTIUTIONS = [
    "I can change the recipe to use what you have at home. Just ask me to replace an ingredient.",
]

NOT_POSSIBLE = [
    "I don't think that this ingredient is in the recipe, so I can't replace it.",
]

###########################
# EXECUTION PHASE PROMPTS #
###########################

EXECUTION_START_INTRO = [
    "Just so you are aware. I can repeat, go back, or say the next step. Let's start.",
]

EXECUTION_NO_CANCEL = [
    "We can't cancel a task that's already in progress.",
]

NO_MORE_DETAILS = [
    "I'm sorry, but that's all I know about this step.",
]

NO_VIDEO = "Unfortunately, I don't have a useful video for this step."

VIDEO_SUGGESTIONS = [
    ". I have found a video that might be relevant.",
]

SEARCH_AGAIN_QUESTION = [
    "It sounds like you want to start a new task. Is that true?",
]

DECLINE_NEW_SEARCH = [
    "No problem, just say next when you are ready to continue. ",
]

###################
# GENERAL PROMPTS #
###################

RIND_FALLBACK_RESPONSE = [
    "Sorry, I had trouble understanding that.",
]

UNSAFE_BOT_RESPONSE = [
    "I'm sorry, I had an internal problem, can we keep going?",
]

PAUSING_PROMPTS = [
    "Conversation paused.",
]

DEFAULT_QA_PROMPTS = [
    "Sorry I'm not sure. Let's continue.",
]

SAFE_FALLBACK_RESPONSE = [
    "what else can I help you with?",
]

###################
# FAREWELL PROMPTS #
###################

COOKING_FAREWELL = [
    "Great job! You finished your cooking task!",
]

DIY_FAREWELL = [
    "Great job! You finished your DIY task!",
]

USER_OPTIONS_PROMPTS = [
    " How about a new recipe? Or say exit to leave the conversation. "
]

STOP_SCREEN_PROMPTS = [
    " Thank you for using the bot, have a good day",
]

###################
# ASR ERR PROMPTS #
###################

ASR_ERROR = ["'{}' sounded like an error."]
