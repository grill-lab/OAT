from abc import abstractmethod, ABC
from taskmap_pb2 import Session, UserRequest


class AbstractParser(ABC):

    @abstractmethod
    # Maybe use UserRequest as return type?
    def __call__(self, session: Session) -> Session:
        # Parsing operation to enrich the session
        pass
