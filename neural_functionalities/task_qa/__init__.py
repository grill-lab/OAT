from .qa_system import NeuralIntraTaskMapContextualQA as DefaultQA
# from .GPT3_qa import GPT3TaskQA as DefaultQA

from .qa_servicer import Servicer
from .qa_servicer import add_TaskQuestionAnsweringServicer_to_server as add_to_server