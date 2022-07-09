from qa import *


qa_config = {
    'class': ComposedQA,
    'kwargs': {
        'classes_list': [
            {
                'class' : GeneralQA,
                'kwargs': {
                    'environ_var': 'EXTERNAL_FUNCTIONALITIES_URL'
                }
            },
            {
                'class' : IntraTaskmapQA,
                'kwargs': {
                    'environ_var': 'NEURAL_FUNCTIONALITIES_URL'
                }
            }
        ],
        'timeout': 10000,  # 1000 ms
    }
}
