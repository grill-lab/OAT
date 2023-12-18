WANT_TO_START = "Do you want to start?"
SAFETY_WARNING = (
    "Before we get started, please be careful when using any tools or equipment."
)
DANGEROUS_RESPONSE = [
    "Actually, I can't help you with potentially dangerous tasks, bye!",
]
DOMAIN_PROMPT = [
    "I know about cooking, home improvement, and arts and crafts. What can I help you with?",
    "I'm excited to help you do some arts and crafts, find a home project, or cook a tasty recipe. What shall we make today?",
    "I can help with cooking, home improvement, and arts and crafts. What would you like to make?",
    ###
    "Finding recipes and walking you through arts and crafts projects is what I do best. "
    "I don't yet know about other areas though. I'd love to help you out with something like, how do I remove a stain from a carpet.",
    "I'm not very fluent in things other than cooking and home improvement. "
    "How about we walk through a recipe together? Ask me: 'how do I make the tastiest scrambled eggs?",
    "If you'd like to cook something or follow an awesome do it yourself project, I'm great at that! "
    "Other areas are still a little tricky for me. The best way I can help is for you to first ask me for a recipe or home project to do. "
    "Here's a hint! 'How do I make new york style pizza'",
]
RESUMING_RESPONSE = "welcome back, let’s continue with"
EARLIER_RESULTS = "these were the top matches I found earlier"
NOT_COMFORTABLE = "I don’t feel comfortable talking about that"
REPROMPT = "What else can I help you with?"
DETAIL_PAGE = "Do you want to see the ingredients?"
DETAIL_PAGE_HEADLESS = "Do you want to hear them?"
DETAIL_PAGE_DIY = "Do you want to see the tools and materials?"
PREFERENCE_ELICITATION_COOKING_1 = ["What's your favorite thing to cook?"]
PREFERENCE_ELICITATION_COOKING_2 = [
    "What about it do you find appealing?",
    "Why do you enjoy it?",
    "What do you love about it?",
]
PREFERENCE_RECOMMENDATIONS = "Okay, I think you might enjoy one of these"
PREFERENCE_ELICITATION_DIY_1 = ["What is your favorite home improvement project?"]
CATCH_ALL_ELICITATION_RESPONSE = [
    "Sorry, I didn't quite understand that.",
    "Please run that by me again.",
    "Pardon me.",
    "Tell me more about why you like your favourite food, and I'll find some recipes you might enjoy!",
]
QA_ELICITATION_RESPONSE = [
    "Pardon me, I'm still learning to answer questions effectively.",
    "Great question. I actually haven't given that much thought yet.",
    "Great question! If I knew the answer, I would tell you.",
    "I'm sorry, I can only answer Cooking or home improvement questions.",
]
NO_DETAILS_AVAILABLE = (
    "I don't know more details about this step. If you want to hear the step again, "
    "say 'repeat' or say 'next' to keep going."
)
REQUIREMENTS_INFO = "Here are the task requirements"
NO_REQ_FOUND = "This task has no requirements"
GO_BACK_TO_TASK = 'You can navigate back to the task by saying "Go back"'
GO_BACK_TO_TASK_NO_REQS = (
    "You can say 'next' to keep going, or say 'repeat' to hear the step again."
)
NAVIGATION_PROMPT = "You can go to the next step by saying 'next',or say 'repeat' to say the step again."
DOMAIN_HELP = "I can help you cook or do some home improvement"
PLANNING_HELP = [
    "This is the summary",
    "What do you think",
    "You are currently previewing",
]
VALIDATION_HELP = [
    "You can see what you need",
    "Would you like to continue",
    "You can navigate through the requirements",
]
EXECUTION_HELP = [
    "You can navigate through the steps",
    "You can ask any question about the requirements",
]
WANT_TO_START_REPROMPT = "Shall we get started with"
THEME_SEARCH = [
    "I have three great recommendations for",
    "I found three great matches",
    "you can try one of my three all-time favorites",
]
SEARCH_RESULTS = [
    "found three great matches",
    "Sure, these recipes are my favourite",
    "Got it, these are my favourites",
    "How about these three matches? They look so tasty",
    "Exciting! Here are my top three picks",
    "I found three great matches for you. ",
    "Sure, these are my favourites",
    "How about these three matches",
    "Got it, these tutorials look interesting",
    "Sounds good! Here are my top three picks",
]
SEARCH_RESULTS_HEADLESS = "The best matches I could find for you are the following"
MEDICAL_RESPONSE_LEVEL_1 = [
    "Sorry I can't give medical advice",
]

MEDICAL_RESPONSE_LEVEL_2 = [
    "I really can't give you any medical advice",
]

FINANCIAL_RESPONSE_LEVEL_1 = [
    "FYI, I can't give you financial advice, my comfort zone for now is cooking and home improvement. "
    "Just imagine! Making food with a robot, pretty cool right? We should try some together!",
]

FINANCIAL_RESPONSE_LEVEL_2 = [
    "I really can't give you financial advice, but, just a humble brag, I'm great at crafts and cooking! "
    "You have to ask me first though, just say: 'new york style pizza', or, 'let's do origami'."
]

LEGAL_RESPONSE_LEVEL_1 = [
    "FYI, I can't give you legal advice, my creators have limited my powers. But I have the power to help you cook and do some cool home projects! "
    "Here's a hint if you're not sure how to start. Try saying: 'cooking'.",
]

LEGAL_RESPONSE_LEVEL_2 = [
    "I really can't give you legal advice, what i'd enjoy most is to walk through a tasty recipe, or a home project together. "
    "Let's try something, imagine a cool crafts project, like 'how to make a picture frame', and we can give it a go! "
    "No pressure, i'd also be a bit flustered if a robot was telling me what to do."
]
REQS_ENUMERATION = [
    "set of",
    "Okay, for starters, you'll need",
    "Finally, you'll need",
    "Awesome. To begin with, you'll have to get",
]

TASK_COMPLETION = ["You have completed", "You just finished"]

EXECUTION_NO_CANCEL = [
    "It's a shame, we can't cancel a task that's already in progress just now. "
    "But we can stop the conversation if you want to start over. No pressure, but I'm excited to keep going!",
    "Gosh, I can't cancel an ongoing task to do a new search. It's out of my control unfortunately. "
    "If you wish to start over, you can stop the conversation. It'd be great to keep going though!",
]

LEVEL_ONE_UNDEFINED_DOMAIN_RESPONSES = [
    "Finding recipes and walking you through arts and crafts projects is what I do best. "
    "I don't yet know about other areas though. I'd love to help you out with something like, how do I remove a stain from a carpet.",
    "I'm not very fluent in things other than cooking and home improvement. "
    "How about we walk through a recipe together? Ask me: 'how do I make the tastiest scrambled eggs?",
    "If you'd like to cook something or follow an awesome do it yourself project, I'm great at that! "
    "Other areas are still a little tricky for me. The best way I can help is for you to first ask me for a recipe or home project to do. "
    "Here's a hint! 'How do I make new york style pizza'",
    "I'm not very fluent in things other than cooking and home improvement. "
    "How about we walk through a recipe together? Ask me: 'find me a recipe for Creamy Lemon Zucchini pasta'",
]

LEVEL_TWO_UNDEFINED_DOMAIN_RESPONSES = [
    "I can help you with a task if you say something like: 'How do I cook a pizza?'. What do feel like doing?",
    "I can help you with a task if you say something like: 'help me make a rice dish', or, "
    "'help me make origami'. What do feel like doing?",
    "By just saying: 'cooking' or 'I want to do arts and crafts', we can walk through finding a great project together! "
    "In your own time, I'm all ears!",
    "Discussing things other than recipes or do it yourself tasks isn't really my strong suit. "
    "What we can do is find a recipe or project to do and walk through it together! "
    "Some of my favourite are: 'making carrot cake', or 'giving a wooden table new life with some varnish'. "
    "Let me know what you'd like.",
    "I think I'd make a mess of anything that isn't cooking or crafts, it's just not what I'm made for. "
    "There are a lot of exciting tasks I know of though! Try me for something specific! Or just say: 'cooking', or 'home improvement', "
    "if you're still undecided.",
]


MORE_RESULTS_INTRO = [
    "Okay. Here are other great options I found. ",
    "Alright. I also found these other matches you might like. ",
    "Not to worry. I have a couple more options for you. ",
    "That's fine. Here are a few others. ",
    "Hmmm. These other matches might interest you. ",
]

PREVIOUS_RESULTS_INTRO = [
    "Sure. Here are the previous matches I found. ",
    "You got it. These were the other options I mentioned. ",
    "Got it. These were the previous options I brought up. ",
    "Okay. These were the options I recommended before. ",
]

ALL_RESULTS_PROMPT = [
    "That's all I've got. If you don't like these matches, you can say cancel to search for something else.",
    "I don't have any more matches for you. At any rate, you can go back to hear the previous results, or say cancel to search for something else.",
    "Bummer. I'd love to tell you more options, however, I only found twelve. You can hear the previous ones again, or say cancel "
    "to search for something else.",
]

NO_PLANNING = [
    "Okay, thanks, let's try again. What would you like do to?",
    "Sure, let's try to search for something again. What would you like to make?",
    "Thanks for the feedback. What would you like to search for?",
]

YES_PLANNING = [
    "Nice, I'm glad! ",
    "Cool, thanks for letting me know. ",
    "Amazing, that's good to know. ",
]

SELECT_POSSIBILITY = [
    "You can select one of the results by saying the name of the result. ",
    "You can also select a result if you'd like. ",
]

FEEDBACK_PLANNING = [
    "Are the results what you were looking for?",
    "Do you like the suggested matches?",
    "Did you find what you were looking for?",
]

MORE_RESULTS_FALLBACK = [
    "I'd love to show you more great matches, but I'm still learning how! "
    "If you want to try something else though, you can say something like, 'search again for rice dishes'!",
]
