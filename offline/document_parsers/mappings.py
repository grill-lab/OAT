from wikihow_parser import WikihowParser
from seriouseats_parser import SeriouseatsParser
from food52_parser import Food52Parser
from foodnetwork_parser import FoodNetworkParser
from epicurious_parser import EpicuriousParser
from tasteofhome_parser import TasteOfHomeParser
from foodandwine_parser import FoodAndWineParser
from doityourself_parser import DoItYourselfParser
from wholefoodsmarket import WholeFoodsParser


document_parser_mappings = {
    'wikihow.com': WikihowParser,
    'seriouseats.com': SeriouseatsParser,
    'food52.com': Food52Parser,
    'foodnetwork.com': FoodNetworkParser,
    'epicurious.com': EpicuriousParser,
    'tasteofhome.com': TasteOfHomeParser,
    'foodandwine.com': FoodAndWineParser,
    'doityourself.com': DoItYourselfParser,
    'wholefoodsmarket.com': WholeFoodsParser
}


document_websites = [
    ('wholefoods', ['wholefoodsmarket.com']),
    ('epicurious', ['epicurious.com']),
    ('seriouseats', ['seriouseats.com']),
    ('food52', ['food52.com']),
    ('foodandwine', ['foodandwine.com']),
    ('foodnetwork', ['foodnetwork.com']),
    ('tasteofhome', ['tasteofhome.com']),
    ('wikihow', ['wikihow.com']),
    ('doityourself', ['doityourself.com'])
]


# potential_taskmap_websites = [
#     # --- Cooking websites ---
#     'allrecipes.com',
#     'bettycrocker.com',
#     'bonapetit.com',
#     'cooking.nytimes.com',
#     'cookinglight.com',
#     'cookscountry.com',
#     'delish.com',
#     'epicurious.com',
#     'food.com',
#     'food52.com',
#     'foodandwine.com',
#     'foodnetwork.com',
#     'kingarthurbaking.com',
#     'recipetineats.com',
#     'seriouseats.com',
#     'simplyrecipes.com',
#     'smittenkitchen.com',
#     'tastemade.com',
#     'tasteofhome.com',
#     'tasty.co',
#     'tastykitchen.com',
#     'thespruceeats.com',
#     'traegergrills.com',
#     'wholefoodmarket.com',
#     'cooking.nytimes.com',
#     # --- Home improvement websites ---
#     'wikihow.com',
#     'doityourself.com',
#     'instructables.com',
#     'familyhandyman.com',
# ]

