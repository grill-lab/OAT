import os
import grpc
import time
import threading

from concurrent.futures import ThreadPoolExecutor

from taskmap_pb2 import Session
from staged_enhancer_pb2 import StageState, StagedOutput
from utils import ProtoDB, logger

from .llm_taskmap_enhancer import LLMTaskMapEnhancer
from llm_pb2 import LLMMultipleDescriptionGenerationRequest
from llm_pb2_grpc import LLMDescriptionGenerationStub


class StagedEnhance:

    def __init__(self, prefix, database_url):
        self.db = ProtoDB(proto_class=StagedOutput,
                          prefix=prefix,
                          url=database_url,
                          primary_key="taskmap_id")

        self.service = LLMTaskMapEnhancer()
        functionalities_channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
        self.llm_desc_generator = LLMDescriptionGenerationStub(functionalities_channel)

    @staticmethod
    def trigger(session) -> bool:
        return "wikihow" in session.task.taskmap.source_url and session.task.state.enhanced is False

    def __get_obj(self, taskmap_id) -> StagedOutput:
        return self.db.get(taskmap_id)

    def __start(self, taskmap, staged_db, output, questions_only):
        def _enhance_taskmap_wrapper(taskmap, staged_db, questions_only):
            try:
                if questions_only:
                    return self.service.proactive_question_enhancement(taskmap, staged_db)
                else:
                    return self.service.enhance_taskmap(taskmap, staged_db)
            except Exception as e:
                logger.exception("Exception while running Task Enhancer", exc_info=e)
                return None

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_enhance_taskmap_wrapper, taskmap, staged_db, questions_only)
                response = future.result(timeout=60)

            if response is not None:
                # Updating output object to ENDED execution and adding the response
                output.taskmap.ParseFromString(response.SerializeToString())
                output.state = StageState.ENDED
                self.db.put(output)
            else:
                output.state = StageState.NONE
                self.db.put(output)

        except TimeoutError:
            logger.info("Timeout while running Task Enhancer")
            output.state = StageState.NONE
            self.db.put(output)

        except Exception as e:
            logger.exception("Exception while running Task Enhancer, reverting StagedOutput object", exc_info=e)
            output.state = StageState.NONE
            self.db.put(output)
            # Clean up in case of an error during Enhancement

    def _enhance_desc(self, session_db, taskmap_db, session: Session) -> None:
        taskmaps_to_enhance = []
        request: LLMMultipleDescriptionGenerationRequest = LLMMultipleDescriptionGenerationRequest()

        for i, candidate in enumerate(session.task_selection.candidates_union):
            # avoid categories
            if candidate.HasField('category'):
                continue

            task_cached = taskmap_db.get(candidate.task.taskmap_id)
            if task_cached.description != "":
                # check if task already cached
                session.task_selection.candidates_union[i].task.CopyFrom(task_cached)
            elif len(candidate.task.description.split(" ")) < 50 and candidate.task.description != "":
                # check if already good description but not yet cached
                taskmap_db.put(candidate.task)
            else:
                taskmaps_to_enhance.append(candidate.task)
                request.task_title.append(candidate.task.title)
                ingredients = [el.amount + " " + el.name for el in candidate.task.requirement_list]
                request.ingredients.append(str(ingredients))
                request.domains.append(candidate.task.domain_name)

        # Return if there is nothing to enhance
        if len(request.task_title) == 0:
            logger.info("Nothing to enhance")
            session_db.put(session)
            return

        # Generate Descriptions and update session     
        descriptions = self.llm_desc_generator.generate_descriptions(request)

        for taskmap, description in zip(taskmaps_to_enhance, descriptions.description):
            taskmap.description = description
            taskmap_db.put(taskmap)

        session_db.put(session)

    def _enhancement_timed_thread(self, function, session_db, taskmap_db, session: Session, default_timeout) -> None:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(function, session_db, taskmap_db, session)
            timeout: float = default_timeout / 1000 + time.monotonic()
            try:
                if future.done() or timeout - time.monotonic() > 0:
                    logger.info("Successful Description Generation")
                else:
                    future.cancel()
                    logger.info("Timeout for Description Generation")
            except TimeoutError as e:
                logger.exception("TimeoutError while running LLM Description Generation", exc_info=e)

    def enhance_descriptions(self, session, session_db, taskmap_db, default_timeout=60000):
        if session.task.phase == 1 and "MoreResultsIntent" not in session.turn[-1].user_request.interaction.intents:
            thread = threading.Thread(target=self._enhancement_timed_thread,
                                      args=(self._enhance_desc, session_db, taskmap_db, session, default_timeout))
            thread.start()

    def enhance(self, session, questions_only=False) -> Session:
        logger.info("ENHANCEMENT START")

        taskmap = session.task.taskmap
        output = self.__get_obj(taskmap.taskmap_id)
        current_state: StageState = output.state

        if current_state == StageState.NONE:
            # Upload Object State to STARTED
            output.state = StageState.STARTED
            output.taskmap.ParseFromString(taskmap.SerializeToString())
            self.db.put(output)

            # Starting Thread for parallel
            thread = threading.Thread(target=self.__start, args=(taskmap, self.db, output, questions_only))
            thread.start()
            return session

        elif current_state == StageState.STARTED:
            # Process is already in progress
            session.task.taskmap.ParseFromString(self.__get_obj(taskmap.taskmap_id).taskmap.SerializeToString())
            return session

        elif current_state == StageState.ENDED:
            # Enhance the TaskMap with the obtained info and return the updated session
            session.task.state.enhanced = True
            session.task.taskmap.ParseFromString(self.__get_obj(taskmap.taskmap_id).taskmap.SerializeToString())
            return session
