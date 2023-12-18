from dangerous_task_pb2_grpc import DangerousServicer, add_DangerousServicer_to_server
from taskmap_pb2 import TaskMap, Session

from . import DefaultDangerousTask
from . import DefaultDangerousRequest


class Servicer(DangerousServicer):

    def __init__(self):
        self.dangerous_task = DefaultDangerousTask()
        self.dangerous_request = DefaultDangerousRequest()

    def dangerous_task_check(self, taskmap: TaskMap, context):
        return self.dangerous_task.test_dangerous_task(taskmap)
    
    def dangerous_query_check(self, session: Session, context):
        return self.dangerous_request.assess_user_request(session)
