import os
import random
import grpc
import re

from typing import Tuple

from utils import (
    logger, set_source, CHITCHAT_GREETINGS, get_helpful_prompt,
    consume_intents, is_in_user_interaction, repeat_screen_response,
    HELPFUL_PROMPT_PAIRS, JOKE_TRIGGER_WORDS, build_joke_screen,
    LEVEL_ONE_MEDICAL_RESPONSES, LEVEL_TWO_MEDICAL_RESPONSES, LEVEL_ONE_LEGAL_RESPONSES,
    LEVEL_TWO_LEGAL_RESPONSES, LEVEL_ONE_FINANCIAL_RESPONSES, LEVEL_TWO_FINANCIAL_RESPONSES,
)
from exceptions import PhaseChangeException

from policy.abstract_policy import AbstractPolicy
from taskmap_pb2 import Session, OutputInteraction, Task, ExtraInfo

from chitchat_classifier_pb2 import ChitChatRequest
from chitchat_classifier_pb2_grpc import ChitChatClassifierStub

from llm_pb2 import LLMChitChatRequest
from llm_pb2_grpc import LLMChitChatStub
from compiled_protobufs.intent_classifier_pb2 import DomainClassification
from compiled_protobufs.intent_classifier_pb2_grpc import IntentClassifierStub

from joke_retriever_pb2_grpc import JokeRetrieverStub
from database_pb2 import Void


class ChitChatPolicy(AbstractPolicy):

    def __init__(self) -> None:

        neural_functionalities_channel = grpc.insecure_channel(os.environ['NEURAL_FUNCTIONALITIES_URL'])
        functionalities_channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])

        self.llm_chit_chat = LLMChitChatStub(functionalities_channel)
        self.chitchat_classifier = ChitChatClassifierStub(neural_functionalities_channel)
        self.joke_retriever = JokeRetrieverStub(functionalities_channel)
        self.domain_classifier = IntentClassifierStub(functionalities_channel)

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

    @staticmethod
    def __get_helpful_prompt(user_query: str) -> str:
        for word in user_query.split(" "):
            for keyword, answer in HELPFUL_PROMPT_PAIRS:
                if word == keyword:
                    return answer

        for keyword, answer in HELPFUL_PROMPT_PAIRS:
            if keyword in user_query:
                return answer

    def step(self, session: Session) -> Tuple[Session, OutputInteraction]:

        if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                  utterances_list=["what can you do"]):
            logger.info('In chit chat, but should actually be help handler -> rerouting')
            del session.turn[-1].user_request.interaction.intents[:]
            session.turn[-1].user_request.interaction.intents.append("InformIntent")
            raise PhaseChangeException()

        elif is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                    utterances_list=JOKE_TRIGGER_WORDS):

            extra_info: ExtraInfo = self.joke_retriever.get_random_joke(Void())
            output = build_joke_screen(session, extra_info=extra_info)
            set_source(output)
            return session, output

        output: OutputInteraction = OutputInteraction()

        if session.task.phase != Task.TaskPhase.DOMAIN:
            domain_response: DomainClassification = self.domain_classifier.classify_domain(session)
            confidence = domain_response.confidence
            top_domain = domain_response.domain
        else:
            top_domain = "NA"
            confidence = "low"

        if top_domain in ["MedicalDomain", "FinancialDomain", "LegalDomain"] and confidence == "high":
            logger.info(f'Domain classification - Chit Chat identified as {top_domain}')
            rule = self.__get_rule(top_domain)
            output.speech_text = rule

        else:

            chitchat_request: ChitChatRequest = ChitChatRequest()
            chitchat_request.text = session.turn[-1].user_request.interaction.text
            chitchat_request.threshold = 0.7

            chitchat_response = self.chitchat_classifier.classify_chitchat(chitchat_request)

            got_llm_response = False
            if chitchat_response.text == "":
                try:
                    llm_chitchat_request = LLMChitChatRequest()
                    llm_chitchat_request.last_user_utterance = session.turn[-2].user_request.interaction.text
                    llm_chitchat_request.user_question = session.turn[-1].user_request.interaction.text
                    llm_chitchat_request.task_title = session.task.taskmap.title
                    llm_chitchat_request.last_agent_response = session.turn[-2].agent_response.interaction.speech_text
                    if len(session.turn[-2].user_request.interaction.intents) > 0:
                        llm_chitchat_request.last_intent = session.turn[-2].user_request.interaction.intents[-1]
                    chitchat_response = self.llm_chit_chat.generate_chit_chat(llm_chitchat_request)

                    if chitchat_response.text != "":
                        if not chitchat_response.text[-1] in [".", ":", ",", "?", "!"]:
                            chitchat_response.text = chitchat_response.text.strip()
                            chitchat_response.text += "."  # add a period at the end of the sentence
                        got_llm_response = True

                except Exception as e:
                    logger.info("Exception while running LLM Chit Chat", exc_info=e)
                    chitchat_request.threshold = 0.3
                    chitchat_response = self.chitchat_classifier.classify_chitchat(chitchat_request)

            tutorial_list = get_helpful_prompt(phase=session.task.phase, task_title=session.task.taskmap.title,
                                               task_selection=session.task_selection, headless=session.headless)
            helpful_prompt = random.choice([tut for tut in tutorial_list if "exit" not in tut])

            # for now, add a helpful prompt if we have just restarted the session or if we get a hi/ hello in chitchat
            if chitchat_response.text in [resp for question, resp in CHITCHAT_GREETINGS]:
                if session.task.phase == Task.TaskPhase.DOMAIN and session.greetings:
                    output.speech_text = f'{helpful_prompt} '
                else:
                    output.speech_text = f'{chitchat_response.text}{helpful_prompt} '

            elif got_llm_response:
                logger.info(f'CHIT CHAT LLM RESPONSE GIVEN: {chitchat_response.text}')
                keyword_helpful_prompt = self.__get_helpful_prompt(chitchat_request.text)
                transition_options = ['But anyway', 'Just wanted to say', 'Just so you know', 'Just to let you know',
                                      'By the way']

                if keyword_helpful_prompt:
                    output.speech_text = f'{chitchat_response.text} {random.choice(transition_options)} {keyword_helpful_prompt.lower()}'
                else:
                    output.speech_text = f'{chitchat_response.text} {random.choice(transition_options)} {helpful_prompt.lower()}'
            elif chitchat_response.text != "":
                output.speech_text = chitchat_response.text

            if output.speech_text == "":
                # chitchat responses are bad, so fallback to confused
                session.turn[-1].user_request.interaction.intents.append("ConfusedIntent")
                consume_intents(session.turn[-1].user_request.interaction,
                                intents_list=["ChitChatIntent"])
                raise PhaseChangeException()
            else:
                output = repeat_screen_response(session, output)

            set_source(output)
            return session, output
