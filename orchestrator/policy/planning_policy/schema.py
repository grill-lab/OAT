from taskmap_pb2 import Session


VAGUE_QUERIES = {
    Session.Domain.COOKING: [
        "peanut butter cornflake cookies",
        "microwave fantasy fudge",
        "frozen fruit smoothie",
        "easy spinach salad with apples walnuts and feta",
        "apple sandwiches with almond butter and granola",
        "buttered noodles",
        "rotisserie chicken salad",
    ],
    Session.Domain.DIY: [
        "how to make a glittery glass mug",
        "create a custom mirror",
        "reupholster furniture",
        "create wall art",
        "how to make graphic string art",
        "create a terrarium",
        "holiday arts and crafts",
    ]
}

# Positional Matching Queries for Reference Resolution when user tries to select
# what the bot has suggested
REFERENCE_QUERIES = {
    Session.Domain.COOKING: [
        "new york style pizza",
        "sauces and soups",
        "Halibut",
        "roasted asparagus and sweet potatoes",
        "grass fed sirloin steak",
        "fruit and vegetables",
        "lasagna",
    ],
    Session.Domain.DIY: [
        "origami",
        "how to make a guitar",
        "gardening",
    ]
}


CONVERSATION_TREE = {
    Session.Domain.COOKING: {
        'personality_prompts': [
            "When I'm hungry, I enjoy making new york style pizza. ",
            # New York style pizza
            "My favorite thing to cook would be stocks, sauces and soups "
            "(though its not my favorite thing to eat). What about you? ",
            # sauces and soups
            "I love cooking Halibut or Seabass. Getting that golden brown on "
            "the top is just heaven. ",
            # Halibut
            "I love roasted anything. Asparagus and Sweet Potatoes are my favorites. It's fast, easy, "
            "and a big bang of deliciousness for very little effort. ",
            # roasted asparagus and sweet potatoes
            "I love to barbecue a nice piece of grass fed sirloin steak with my own dry rub all over it. ",
            # grass fed sirloin steak
            "I love working with whatever fruits and vegetables are in season. "
            "The produce market is a treasure chest as far as I'm concerned. ",
            # fruit and vegetables
            "I love making lasagna. The smell alone is enough to kick my appetite into high gear. ",
            # lasagna
        ],
        'elicitation_questions': [
            "What's your favorite thing to cook?",
        ],
        'responses': {
            'turns': [
                {
                    'ThemeSearchIntent': '',
                    'VagueSearchIntent': '',
                    'SpecificSearchIntent': [
                        "I enjoy that too! What about it do you find appealing?",
                        "That's interesting! Why do you enjoy it?",
                        "Excellent choice! What do you love about it?",
                        "Great choice! What about it do you find appealing?"
                    ],
                    'SelectIntent': '',
                },
                {
                    'VagueSearchIntent': '',
                    'SpecificSearchIntent': '',
                    'ThemeSearchIntent': '',
                }
            ],
            'general': {
                'CancelIntent': '',
                'AMAZON.CancelIntent': '',
                'QAIntent': [
                    "Pardon me, I'm still learning to answer questions effectively. But tell me, what's "
                    "your favourite food?",
                    "Great question. I actually haven't given that much thought yet. Tell me though, "
                    "what's your favourite food?",
                    "Great question! If I knew the answer, I would tell you. Tell me though, what's "
                    "your favourite food?"
                ],
                'OutOfDomainQAIntent': [
                    "I'm sorry, I can only answer Cooking or home improvement questions. But tell me, what's your "
                    "favourite food?"
                ],
                'default': [
                    "Sorry, I didn't quite understand that. What's your favourite food?",
                    "Please run that by me again. What's your favourite food?",
                    "Pardon me. What's your favourite food again?",
                ]
            }
        }
    },
    Session.Domain.DIY: {
        'personality_prompts': [
            "I love Origami a lot because it's so relaxing. When you fold Origami, "
            "everything goes blank except what you're folding. ",
            # Origami
            "I recently developed an interest in playing and building Harps. "
            "I'm currently working on making my first one ever. ",
            # how to make a guitar
            "I really enjoy gardening because it is healthy, beautiful, and rewarding. "
            "I especially love being in my garden and experiencing the scientific process going on around me. "
            # gardening
        ],
        'elicitation_questions': [
            "What is your favorite home improvement project?"
        ],
        'responses': {
            'turns': [
                {
                    'VagueSearchIntent': '',
                    'SpecificSearchIntent': '',
                    'ThemeSearchIntent': '',
                    'SelectIntent': ''
                }
            ],
            'general': {
                    'CancelIntent': '',
                    'AMAZON.CancelIntent': '',
                    'QAIntent': [
                        "Pardon me, I'm still learning to answer questions effectively. What's your favourite "
                        "home improvement project?",
                        "Great question. I actually haven't given that much thought yet. Tell me though, what "
                        "home improvement projects do you enjoy?",
                        "Great question! If I knew the answer, I would tell you. Tell me though, what home improvement "
                        "project do you enjoy in your spare time?",
                    ],
                    'OutOfDomainQAIntent': [
                        "I'm sorry, I can only answer Cooking or home improvement questions. "
                        "But tell me, what home improvement project do you enjoy in your spare time?"
                    ],
                    'default': [
                        "Sorry, I didn't quite understand that. What's your favourite home improvement project?",
                        "Please run that by me again. What home improvement projects do you enjoy?",
                        "Pardon me. What home improvement project do you enjoy in your spare time?",
                    ]
            }
        }
    },
}
