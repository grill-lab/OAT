from policy.abstract_policy import AbstractPolicy
from taskmap_pb2 import (
    Session,
    OutputInteraction,
    Task,
    InputInteraction
)

from .schema import (
    CONVERSATION_TREE,
    VAGUE_QUERIES,
    REFERENCE_QUERIES
)
from exceptions import PhaseChangeException
from utils import (
    repeat_screen_response,
    is_in_user_interaction,
    consume_intents,
    close_session,
    logger
)
import random


class ElicitationPolicy(AbstractPolicy):

    @staticmethod
    def __get_reference_query(session):
        past_agent_prompt = session.task.state.elicitation_personality_prompt

        for query, personality_prompt in zip(REFERENCE_QUERIES[session.domain],
                                             CONVERSATION_TREE[session.domain]['personality_prompts']):
            if personality_prompt == past_agent_prompt:
                return query
        return ''

    def __match_response_model(self, session, response_model):
        for intent, responses in response_model.items():
            if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                      intents_list=[intent]):
                if not responses:
                    return ''
                else:
                    return random.choice(responses)

        if 'default' in response_model.keys():
            return random.choice(response_model['default'])
        else:
            return ''

    def __update_elicitation_utterances(self, session: Session, user_interaction: InputInteraction):
        # Method that updates the user Utterances in some specific cases to enable the
        # system to search for the right items based on the user responses

        if is_in_user_interaction(user_interaction=user_interaction,
                                  intents_list=['SpecificSearchIntent',
                                                'ThemeSearchIntent']):
            session.task_selection.elicitation_utterances.append(user_interaction.text)

        elif is_in_user_interaction(user_interaction=user_interaction,
                                    intents_list=['SelectIntent']):
            query = self.__get_reference_query(session)
            if query is not '':
                session.task_selection.elicitation_utterances.append(query)
            else:
                logger.warning('EMPTY REFERENCE QUERY')

        elif is_in_user_interaction(user_interaction=user_interaction,
                                    intents_list=['VagueSearchIntent']):
            query = random.choice(VAGUE_QUERIES[session.domain])
            session.task_selection.elicitation_utterances.append(query)

    def step(self, session: Session) -> (Session, OutputInteraction):

        output = OutputInteraction()
        user_interaction: InputInteraction = session.turn[-1].user_request.interaction

        logger.info(f"User Intents detected: {user_interaction.intents}")

        # SAFETY CHECK
        if is_in_user_interaction(user_interaction=user_interaction,
                                  intents_list=['DangerousQueryIntent']):
            output.speech_text = "I’m sorry, I can’t help with this type of task."
            session, output = close_session(session, output)
            return session, output

        # OUTPUT SPEECH
        if session.task_selection.elicitation_turns == 0:
            # Entry Utterance
            sub_tree = CONVERSATION_TREE[session.domain]

            session.task.state.elicitation_personality_prompt = random.choice(sub_tree['personality_prompts'])
            output.speech_text = (
                session.task.state.elicitation_personality_prompt +
                random.choice(sub_tree['elicitation_questions'])
            )
            session.task_selection.elicitation_turns += 1
        else:
            # From the second interaction we are starting to update the elicitation Utterances
            self.__update_elicitation_utterances(session, user_interaction)

            turn: int = session.task_selection.elicitation_turns-1
            response_model = CONVERSATION_TREE[session.domain]['responses']['turns'][turn]

            # Processing of the turn-specific Schema
            output.speech_text = self.__match_response_model(session, response_model)

            if output.speech_text != '':
                # If matching one of the Elicitation Turn Intents, increase the Elicitation Turns
                session.task_selection.elicitation_turns += 1
            else:
                response_model = CONVERSATION_TREE[session.domain]['responses']['general']

                # Processing of general catch-all Intents
                output.speech_text = self.__match_response_model(session, response_model)

        # Copy old-screen interface to keep it consistent
        output = repeat_screen_response(session, output)

        return session, output
