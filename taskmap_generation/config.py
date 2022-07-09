import sys
sys.path.insert(0, '/shared')

from utils import get_file_system

# --- Wikihow ---
from datasets.wikihow_dataset import WikihowDataset
from convertors.wikihow_convertor import WikihowConvertor

# --- Seriouseats ---
from datasets.seriouseats_dataset import SeriouseatsDataset
from convertors.seriouseats_convertor import SeriouseatsConvertor

from index_builder.pyserini_index_builder import PyseriniIndexBuilder


################ Datasets  ################
wikihow_config = {
    'Dataset': WikihowDataset,
    'dataset_kwargs': {
        # "categories": ['Home and Garden', 'Hobbies and Crafts'],
        "max_length": 100,
    },
    'dataset_name': 'wikihow',
    'k': 5000,
    'Convertor': WikihowConvertor
}

seriouseats_config = {
    'Dataset': SeriouseatsDataset,
    'dataset_kwargs': {
        "max_length": 200
    },
    'dataset_name': 'seriouseats',
    'k': 1000,
    'Convertor': SeriouseatsConvertor
}
##########################################

################ Config  #################
config_dict = {
    'file_system_path': get_file_system(),
    'version': "0.3.1",
    'datasets': [wikihow_config, seriouseats_config],
    'IndexBuilder': PyseriniIndexBuilder,
    'generate_dense_index': False,
    'output_dir': "system_index",
}
##########################################


