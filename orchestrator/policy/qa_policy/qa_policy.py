import os
import random
import grpc
import re

from typing import Tuple

from dangerous_task_pb2_grpc import DangerousStub
from intent_classifier_pb2_grpc import IntentClassifierStub
from phase_intent_classifier_pb2 import QuestionClassificationRequest
from phase_intent_classifier_pb2_grpc import PhaseIntentClassifierStub
from compiled_protobufs.intent_classifier_pb2 import DomainClassification

from policy.abstract_policy import AbstractPolicy
from qa_pb2 import QAQuery, QARequest
from qa_pb2_grpc import QuestionAnsweringStub, TaskQuestionAnsweringStub
from taskmap_pb2 import OutputInteraction, Session, Task

from utils import (
    logger, set_source, CHITCHAT_FALLBACK, consume_intents,
    LEVEL_ONE_MEDICAL_RESPONSES, LEVEL_TWO_MEDICAL_RESPONSES, LEVEL_ONE_LEGAL_RESPONSES,
    LEVEL_TWO_LEGAL_RESPONSES, LEVEL_ONE_FINANCIAL_RESPONSES, LEVEL_TWO_FINANCIAL_RESPONSES,
    is_in_user_interaction
)
from exceptions import PhaseChangeException


class QAPolicy(AbstractPolicy):

    def __init__(self) -> None:

        functionalities_channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
        neural_functionalities_channel = grpc.insecure_channel(os.environ['NEURAL_FUNCTIONALITIES_URL'])
        external_functionalities_channel = grpc.insecure_channel(os.environ['EXTERNAL_FUNCTIONALITIES_URL'])

        self.qa_systems = {
            "GENERAL_QA": QuestionAnsweringStub(functionalities_channel),  # all three searchers in one
            "Evi_QA": QuestionAnsweringStub(external_functionalities_channel),
            "Neural_General_QA": QuestionAnsweringStub(neural_functionalities_channel),
            "Neural_Task_QA": TaskQuestionAnsweringStub(neural_functionalities_channel),
        }

        self.domain_classifier = IntentClassifierStub(functionalities_channel)
        self.dangerous_task_filter = DangerousStub(external_functionalities_channel)

        self.phase_intent_classifier = PhaseIntentClassifierStub(
            neural_functionalities_channel)

    @staticmethod
    def __get_rule(domain):
        pick = ""
        if domain == "MedicalDomain":
            pick = random.choice(random.choice([LEVEL_TWO_MEDICAL_RESPONSES, LEVEL_ONE_MEDICAL_RESPONSES]))
        elif domain == "FinancialDomain":
            pick = random.choice(random.choice([LEVEL_ONE_FINANCIAL_RESPONSES, LEVEL_TWO_FINANCIAL_RESPONSES]))
        elif domain == "LegalDomain":
            pick = random.choice(random.choice([LEVEL_ONE_LEGAL_RESPONSES, LEVEL_TWO_LEGAL_RESPONSES]))

        sentences = re.split(r'(?<=[.!?])\s+', pick)
        return sentences[0]

    def step(self, session: Session) -> Tuple[Session, OutputInteraction]:
        """Step method for the QAPolicy class.

        This method makes a call to the PhaseIntentClassifier's ``classify_question``
        method to determine the type of question being asked. 

        There are two possible outcomes:

        - if the question is classed as one of the recognised types (e.g. ingredients), then
          the response text is generated by calling the TaskQuestionAnswering service in
          neural_functionalities
        - otherwise the response text is generated by calling the general QuestionAnswering
          service, also in neural_functionalities. 

        The response text is stored in a new OutputInteraction and then returned to 
        the caller. 

        Args:
            session (Session): the current Session object

        Returns:
            tuple(updated Session, OutputInteraction)
        """

        output: OutputInteraction = OutputInteraction()

        if session.task.phase != Task.TaskPhase.DOMAIN:
            domain_response: DomainClassification = self.domain_classifier.classify_domain(session)
            confidence = domain_response.confidence
            top_domain = domain_response.domain
        else:
            top_domain = "NA"
            confidence = "low"

        if top_domain in ["MedicalDomain", "FinancialDomain", "LegalDomain"] and confidence == "high":
            logger.info(f'Domain classification - QA identified as {top_domain}')
            rule = self.__get_rule(top_domain)
            output.speech_text = rule
            set_source(output)
            return session, output

        qa_request: QARequest = QARequest()
        qa_query: QAQuery = QAQuery()

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  intents_list=["DetailsIntent"]):
            qa_query.text = "more details"
        else:
            qa_query.text = session.turn[-1].user_request.interaction.text

        if len(session.turn) > 1:
            qa_query.conv_hist_user = session.turn[-2].user_request.interaction.text
            qa_query.conv_hist_bot = session.turn[-2].agent_response.interaction.speech_text
        qa_query.phase = session.task.phase
        qa_query.taskmap.CopyFrom(session.task.taskmap)
        qa_query.state.CopyFrom(session.task.state)
        qa_query.domain = session.domain
        qa_query.task_selection.CopyFrom(session.task_selection)
        if len(session.turn[-2].user_request.interaction.intents) > 0:
            qa_query.last_intent = session.turn[-2].user_request.interaction.intents[-1]
        qa_request.query.MergeFrom(qa_query)

        qa_classification_request: QuestionClassificationRequest = QuestionClassificationRequest()
        qa_classification_request.utterance = session.turn[-1].user_request.interaction.text
        question_type = self.phase_intent_classifier.classify_question(qa_classification_request).classification
        qa_request.question_type = question_type

        logger.info(f'Question classified as: {question_type}')

        if "replace" or "substitute" in session.turn[-1].user_request.interaction.text.lower() \
                and question_type != "ingredient substitution":
            logger.info(f'Overwriting classification to Ingredient Substitution for: '
                        f'{session.turn[-1].user_request.interaction.text}')
            question_type = "ingredient substitution"
            qa_request.question_type = question_type

        output: OutputInteraction = OutputInteraction()
        if question_type in ["ingredient question", "current task question", "step question", "ingredient substitution",
                             "current viewing options question"]:
            response = self.qa_systems['GENERAL_QA'].synth_response(qa_request)
            output.speech_text = response.text
            if question_type == "ingredient substitution" and len(response.replacement.replacement.name) != "" and \
                response.replacement.replacement.name not in \
                    [ing.replacement.name for ing in session.task.taskmap.replaced_ingredients]:
                session.task.taskmap.replaced_ingredients.append(response.replacement)
        elif question_type in ["system capabilities question"]:
            logger.info('Rerouting to Confused Handling!')
            session.turn[-1].user_request.interaction.intents.append("InformIntent")
            consume_intents(session.turn[-1].user_request.interaction,
                            intents_list=["QuestionIntent"])
            raise PhaseChangeException()
        else:  # "other domain question", "general cooking or DIY question", "chit chat"
            output.speech_text = self.qa_systems["GENERAL_QA"].synth_response(qa_request).text
            
        if output.speech_text == "":
            logger.info('Something went wrong, all QA systems returned None')
            output.speech_text = random.choice(CHITCHAT_FALLBACK)

        set_source(output)
        return session, output
