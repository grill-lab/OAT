from searcher import *

# searcher_config = {
#     'class': FixedSearcher,
#     'kwargs': {
#         'file_list': [
#             "cookies.proto"
#         ]
#     }
# }

searcher_config = {
    'class': ComposedSearcher,
    'kwargs': {
        'classes_list': [
            {
                'class': SearcherPyserini,
                'kwargs': {
                    'index_path': '/shared/file_system/indexes/system_index',
                }
            }
        ],
        'timeout': 10000,  # 1000 ms
    }
}