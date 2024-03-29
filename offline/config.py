import sys
import os

from utils import get_file_system

from augmenters.requirements_augmenter import RequirementsAugmenter
from augmenters.steps_text_augmenter import StepTextAugmenter
from augmenters.thumbnail_image_augmenter import ImageThumbnailAugmenter
from augmenters.step_image_augmenter import StepImageAugmenter
from augmenters.joke_augmenter import JokeAugmenter
from augmenters.fact_augmenter import FactAugmenter
from augmenters.step_splitting_augmenter import StepSplittingAugmenter
from augmenters.audio_video_step_alignment import AudioVideoStepAlignment

from video_index.build_video_index import VideoIndexBuilder
from video_index.build_audio_index import AudioIndexBuilder

from document_parsers.wholefoodsmarket import WholeFoodsParser
from document_parsers.wikihow_parser import WikihowParser
from document_parsers.seriouseats_parser import SeriouseatsParser
from document_parsers.food52_parser import Food52Parser
from document_parsers.epicurious_parser import EpicuriousParser
from document_parsers.foodandwine_parser import FoodAndWineParser
from document_parsers.foodnetwork_parser import FoodNetworkParser
from document_parsers.allrecipes_parser import AllRecipesParser

from url_downloaders import CommonCrawl, Scraper
from taskgraph_construction import TaskgraphConstruction
from augmentations_iterator import AugmentationsIterator
from search_index.composed_index_builder import ComposedIndexBuilder

from task_filters.filter_composed import ComposedFilter
from task_filters.filter_dangerous import DangerousTaskFilter
from task_filters.filter_duplicates import DuplicatesFilter
from task_filters.filter_single_step import SingleStepFilter
from task_filters.filter_suicide import SuicideTaskFilter
from task_filters.filter_sensitive import SensitiveTaskFilter
from task_filters.filter_privacy import PrivacyTaskFilter

from knowledge_corpus.seriouseats_knowledge_parser import SeriouseatsKnowledgeParser
from knowledge_corpus.knowledge_index_builder import KnowledgeIndexBuilder
from knowledge_corpus.knowledge_corpus_runner import KnowledgeCorpusBuilder

from category_index.seriouseats_taxonomy_builder import SeriousEatsTaxonomyBuilder
from category_index.wikihow_taxonomy_builder import WikihowTaxonomyBuilder
from category_index.run_building_taxonomy import TaxonomyBuildRunner
from category_index.category_index_builder import CategoryIndexBuilder

from theme_upload.build_themes import ThemeBuilder

sys.path.insert(0, '/shared')

wikihow_config = {
    'file_path': 'wikihow',
    'parser': WikihowParser,
}

wholefoods_config = {
    'file_path': 'wholefoods',
    'parser': WholeFoodsParser,
}

seriouseats_config = {
    'file_path': "seriouseats",
    'parser': SeriouseatsParser
}

seriouseats_scraped_config = {
    'file_path': "seriouseats_scraped",
    'parser': SeriouseatsParser,
}

food52_config = {
    'file_path': "food52",
    'parser': Food52Parser,
}

epicurious_config = {
    'file_path': "epicurious",
    'parser': EpicuriousParser,
}

foodandwine_config = {
    'file_path': "foodandwine",
    'parser': FoodAndWineParser,
}

foodnetwork_config = {
    'file_path': "foodnetwork",
    'parser': FoodNetworkParser,
}

seriouseats_knowledge_config = {
    'file_path': 'seriouseats',
    'parser': SeriouseatsKnowledgeParser
}

seriouseats_cat_config = {
    'file_path': 'seriouseats',
    'parser': SeriousEatsTaxonomyBuilder

}

wikihow_cat_config = {
    'file_path': 'wikihow',
    'parser': WikihowTaxonomyBuilder,
}

wikihow_scraped_config = {
    'file_path': 'wikihow_scraped',
    'parser': WikihowTaxonomyBuilder,
}

allrecipes_config = {
    'file_path': 'allrecipes',
    'parser': AllRecipesParser,
}

allrecipes_scraped_config = {
    'file_path': 'allrecipes_scraped',
    'parser': AllRecipesParser,
}

offline_config = {
    'steps': [
        {
            'enable': False,
            'step': 'Get HTMLs from Common Crawl',
            'class': CommonCrawl,
            'kwargs': {
                'common_crawl_path': os.path.join(get_file_system(),
                                                  'offline/athena_queries/new_queries_100.csv'),
                'html_proto_path': os.path.join(get_file_system(), 'offline/protos/htmls'),
                'domains_to_run': [wikihow_config, seriouseats_config, epicurious_config, food52_config,
                                   foodnetwork_config, foodandwine_config, wholefoods_config],
            }
        },
        {
            'enable': True,
            'step': 'Get HTML data via direct scraping',
            'class': Scraper,
            'kwargs': {
                'scraper_csv_path': os.path.join(get_file_system(), 'offline/non_cc_urls.csv'),
                'html_proto_path': os.path.join(get_file_system(), 'offline/protos/htmls'),
                'domains_to_run': [allrecipes_scraped_config],
                # add any custom HTTP headers required (default is an empty dict)
                # these are required for allrecipes.com
                'custom_headers': {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept-Language": "en-GB,en;q=0.5",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Pragma": "no-cache",
                    "Cache-Control": "no-cache",
                },
            }
        },
        {
            'enable': True,
            'step': 'Categories Corpus Construction',
            'class': TaxonomyBuildRunner,
            'kwargs': {
                'html_proto_path': os.path.join(get_file_system(), 'offline/protos/htmls'),
                'tasks_that_require_scraping_path': os.path.join(get_file_system(),
                                                                 'offline/athena_queries/new-tasks2.csv'),
                'knowledge_proto_path': os.path.join(get_file_system(), 'offline/protos/categories'),
                'parsers': [wikihow_cat_config, seriouseats_cat_config],
                'objects_index_dir': os.path.join(get_file_system(), 'offline/category_index/objects_idx'),
                'index_builder': CategoryIndexBuilder
            }
        },
        {
            'enable': False,
            'step': 'Build Scraped HTMLS',
            'class': Scraper,
            'kwargs': {
                # note that this file is generated by the categories component above!
                'scraper_csv_path': os.path.join(get_file_system(), 'offline/athena_queries/new-tasks2.csv'),
                'html_proto_path': os.path.join(get_file_system(), 'offline/protos/htmls'),
                'domains_to_run': [seriouseats_scraped_config, wikihow_scraped_config],
            }
        },
        {
            'enable': True,
            'step': 'Taskgraph Construction',
            'class': TaskgraphConstruction,
            'kwargs': {
                'html_proto_path': os.path.join(get_file_system(), 'offline/protos/htmls'),
                # keep consistent with *build corpus -> html_proto_path*
                'taskgraph_proto_path': os.path.join(get_file_system(), 'offline/protos/taskgraphs'),
                # only change when adding a new parser
                'parsers': [wikihow_config, seriouseats_config, epicurious_config, food52_config, foodnetwork_config,
                            foodandwine_config, allrecipes_config],
                # change this to determine which domains you want to parse
                'parse_domains': [wikihow_config, seriouseats_config, epicurious_config, food52_config,
                                  foodnetwork_config, foodandwine_config,
                                  seriouseats_scraped_config, wikihow_scraped_config, allrecipes_scraped_config],
                # select which domains to parse (leave empty if you wish to parse all)
            }
        },
        {
            'enable': True,
            'step': 'Taskgraph Filters',
            'class': ComposedFilter,
            'kwargs': {
                'path_in': os.path.join(get_file_system(), 'offline/protos/taskgraphs'),
                'path_out': os.path.join(get_file_system(), 'offline/protos/taskgraphs_filtered'),
                'task_filters': [DangerousTaskFilter, DuplicatesFilter, SingleStepFilter, SuicideTaskFilter,
                                 SensitiveTaskFilter, PrivacyTaskFilter]
            }
        },
        {
            'enable': True,
            'step': 'Knowledge Corpus Building',
            'class': KnowledgeCorpusBuilder,
            'kwargs': {
                'html_proto_path': os.path.join(get_file_system(), 'offline/protos/htmls'),
                'parsers': [seriouseats_knowledge_config],
                'index_builder': KnowledgeIndexBuilder,
                'knowledge_proto_path': os.path.join(get_file_system(), 'offline/protos/knowledge'),
                'knowledge_index_search_dir': os.path.join(get_file_system(), "offline", "knowledge_indexes",
                                                           "search_idx"),
                'knowledge_index_objects_dir': os.path.join(get_file_system(), "offline", "knowledge_indexes",
                                                            "objects_idx"),
            }
        },
        {
            'enable': True,
            'step': 'Audio index Builder',
            'class': AudioIndexBuilder,
            'kwargs': {
                'temp_dir': os.path.join(get_file_system(), 'offline', 'transcript_temp'),
                'index_dir': os.path.join(get_file_system(), "offline", "system_indexes", "audio_index")
            }
        },
        {
            'enable': True,
            'step': 'Video index Builder',
            'class': VideoIndexBuilder,
            'kwargs': {
                'temp_metadata': os.path.join(get_file_system(), "offline", 'video_temp'),
                'index_dir': os.path.join(get_file_system(), "offline", "system_indexes", "video_index-simple")
            }
        },
        {
            'enable': True,
            'step': 'Taskgraph Augmentations',
            'class': AugmentationsIterator,
            'kwargs': {
                'taskgraph_proto_path': os.path.join(get_file_system(), 'offline/protos/taskgraphs_filtered'),
                'augmented_taskgraph_proto_path': os.path.join(get_file_system(),
                                                               'offline/protos/augmented-taskgraphs'),
                'augmenters': [RequirementsAugmenter, ImageThumbnailAugmenter, StepImageAugmenter,
                               StepSplittingAugmenter, JokeAugmenter, FactAugmenter],  # AudioVideoStepAlignment
                'augment_domains': [wikihow_config, seriouseats_config, epicurious_config, food52_config,
                                    foodnetwork_config, foodandwine_config,
                                    seriouseats_scraped_config, wikihow_scraped_config, allrecipes_scraped_config],
                # select which domains to parse (leave empty if you wish to parse all)
            }
        },
        {
            'enable': True,
            'step': 'Index Builder',
            'class': ComposedIndexBuilder,
            'kwargs': {
                'rebuild_objects_only': False,
                # if the taskgraph content that affects indexing is not changed, only rebuild the object index
                'taskgraph_proto_path': os.path.join(get_file_system(), 'offline/protos/augmented-taskgraphs'),
                'taskgraph_proto_path_flattened': os.path.join(get_file_system(),
                                                               'offline/protos/augmented-taskgraphs-flattened'),
                'category_proto_path': os.path.join(get_file_system(), "offline/protos/categories"),
                # keep consistent with the path in 'Categories Corpus Construction'
                'index_search_dir_sparse': os.path.join(get_file_system(), "offline", "system_indexes", "search_idx",
                                                        "sparse"),
                'index_search_dir_dense': os.path.join(get_file_system(), "offline", "system_indexes", "search_idx",
                                                       "dense"),
                'index_objects_dir': os.path.join(get_file_system(), "offline", "system_indexes", "objects_idx"),
            }
        },
        # run the theme builder script. this depends on the system index created by the previous
        # entry, so it must be run after those files have been created
        {
            'enable': True,
            'step': 'Theme Builder',
            'class': ThemeBuilder,
            'kwargs': {
                # paths to the system indexes
                'index_sparse_path': os.path.join(get_file_system(), "offline", "system_indexes", "search_idx",
                                                        "sparse"),
                'index_objects_path': os.path.join(get_file_system(), "offline", "system_indexes", "objects_idx"),
                # JSON file defining theme information
                'theme_json_path': '/source/theme_upload/theme_recommendations.json',
                # path where JSON dump of TaskGraphs matching the themes will be written to
                'theme_data_output_path': '/source/theme_upload/themes.json',
                # if True, upload the created themes to the local DynamoDB instance. I
                # If False, only generate the themes JSON file. 
                'upload_themes': True,
            }
        }
    ]
}
