from abc import ABC, abstractmethod
from taskmap_pb2 import Session
from qa_pb2 import QAQuery, QARequest, QAResponse, DocumentList


class AbstractQA(ABC):

    @abstractmethod
    def rewrite_query(self, session: Session) -> QAQuery:
        """
        This method takes the current user utterance from the session and re-writes
        it so that it is a self-contained query to obtain the answer.
        Example: "How many did I need?" -> "How many eggs did I need?"
        We can use all available information in the session (taskmap, previous utterances, system responses)
        to synthesise this rewritten query.
        :param session: {turn:[...], task:{...}...}
        :return: QAQuery: {text: "..", top_k: 1}
        """
        pass

    @abstractmethod
    def domain_retrieve(self, query: QAQuery) -> DocumentList:
        """
        This method retrieves domain specific extrinsic knowledge relating to the query.
        It provides a support set using one or many search systems.
        :param query: {text: "..", top_k: 1}
        :return: DocumentList: {sources: [Document,..]}
        """
        pass

    @abstractmethod
    def synth_response(self, request: QARequest) -> QAResponse:
        """
        This method is responsible for synthesizing the final answer to the query.
        It is the final form that will be uttered to the user.
        The method should outline a way to integrate all information in the QARequest to generate the answer.
        :param request: {query: QAQuery, list: DocumentList, taskmap: TaskMap}
        :return: QAResponse: {text: ".."}
        """
        pass