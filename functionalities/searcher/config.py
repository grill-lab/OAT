from utils import Downloader

from searcher import ComposedSearcher, SearcherPyserini, RemoteSearcher

artefact_ids = ["objects_idx", "category_idx", "sparse_search_idx", "dense_search_idx"]
downloader = Downloader()
downloader.download(artefact_ids)

searcher_config = {
    'class': ComposedSearcher,
    'kwargs': {
        'classes_list': [
            {
                'class': SearcherPyserini,
                'kwargs': {
                    # 'index_path': '/shared/file_system/indexes/system_index',
                    'sparse_searcher_path': downloader.get_artefact_path("sparse_search_idx"),
                    # pipeline search index
                    'task_dir': downloader.get_artefact_path("objects_idx"),
                    # for retrieving taskgraph objects
                    'category_dir': downloader.get_artefact_path("category_idx"),
                    # index for retrieving category objects
                    'dense_index_path': downloader.get_artefact_path("dense_search_idx"),
                }
            },
            {
                'class': RemoteSearcher,
                'kwargs': {
                    'environ_var': 'EXTERNAL_FUNCTIONALITIES_URL'
                }
            }
        ],
        'timeout': 10000,  # 1000 ms
    }
}
