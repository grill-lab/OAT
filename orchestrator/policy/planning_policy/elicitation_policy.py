import random
import grpc
import os
from typing import Dict, Tuple

from policy.abstract_policy import AbstractPolicy
from taskmap_pb2 import InputInteraction, OutputInteraction, ScreenInteraction, Session, Image, TaskmapCategoryUnion
from searcher_pb2 import CategoryIDs, CategoryResults
from searcher_pb2_grpc import SearcherStub
from exceptions import PhaseChangeException

from utils import (
    close_session,
    is_in_user_interaction,
    logger,
    repeat_screen_response,
    set_source,
    consume_intents
)

from .schema import CONVERSATION_TREE, REFERENCE_QUERIES, VAGUE_QUERIES, RECOMMENDED_CATEGORIES


class ElicitationPolicy(AbstractPolicy):
    
    def __init__(self):
        channel = grpc.insecure_channel(os.environ['FUNCTIONALITIES_URL'])
        self.searcher = SearcherStub(channel)
        self.category_recommendations = CategoryResults()
        self.recommendations_count = 0

    @staticmethod
    def __get_reference_query(session: Session) -> str:
        """Looks up a reference query based on the current Session.

        Checks the value of ``session.task.state.elicitation_personality_prompt`` against
        each of the personality prompts defined for the current domain. The prompt field
        is only used in this policy, and is populated the first time the policy is triggered.

        The point of this method is to backtrack from the response and retrieve the 
        corresponding query. 

        Args:
            session (Session): the current Session object

        Returns:
            the matched query, or an empty string if no match
        """
        past_agent_prompt = session.task.state.elicitation_personality_prompt

        for query, personality_prompt in zip(REFERENCE_QUERIES[session.domain],
                                             CONVERSATION_TREE[session.domain]['personality_prompts']):
            if personality_prompt == past_agent_prompt:
                return query
        return ''

    @staticmethod
    def __match_response_model(session: Session, response_model: Dict) -> str:
        """Given a "response model", select output speech text.

        The data structures in schema.py include "response models" for each domain. These are dicts
        with keys "turns" (a list of dicts mapping intent names to lists of speech responses) and "general"
        (a single dict with the same structure). The ``response_model`` parameter here will be
        one of these dicts, containing one or more intent:response mappings. 

        The method will iterate over the items in the dict and check if each intent appears
        in the current InputInteraction. If an intent is matched but no responses exist, an
        empty string is returned, otherwise a random choice is made from the list of responses.

        If no intents match but the model dict has a "default" key, a random choice of response is
        made from its list of responses. If this also fails, an empty string is returned.

        Args:
            session (Session): the current Session object
            response_model (Dict): a "response model" Dict mapping intent names to lists of response (see schema.py)

        Returns:
            a possibly empty string containing a speech text response
        """
        for intent, responses in response_model.items():
            if is_in_user_interaction(user_interaction=session.turn[-1].user_request.interaction,
                                      intents_list=[intent]):
                if not responses:
                    return ''
                else:
                    return random.choice(responses)

        if 'default' in response_model.keys():
            return 'default'
        else:
            return ''

    def __update_elicitation_utterances(self, session: Session, user_interaction: InputInteraction) -> None:
        """Update the elicitation_utterances in the Session for better searching.

        This method will append an entry to the ``session.task_selection.elicitation_utterances``
        list in a few different circumstances:

        - the current InputInteraction contains a SpecificSearchIntent/ThemeSearchIntent, in
          which case the current utterance is appended to the list
        - the current InputInteraction contains a SelectIntent. In this case, a call to 
          __get_reference_query is used to retrieve the query that corresponds to a previous
          personality response from this policy, and that query (e.g. "gardening") is added to
          the elicitation utterances
        - the current InputInteraction contains a VagueSearchIntent. If this happens, a random choice
          made from the VAGUE_QUERIES dict in schema.py, and the result added to the list

        Args:
            session (Session): the current Session object
            user_interaction (InputInteraction): the most recent InputInteraction in the Session
        """
        if is_in_user_interaction(user_interaction=user_interaction,
                                  intents_list=['SpecificSearchIntent',
                                                'ThemeSearchIntent']):
            session.task_selection.elicitation_utterances.append(user_interaction.text)

        elif is_in_user_interaction(user_interaction=user_interaction,
                                    intents_list=['SelectIntent']):
            query = self.__get_reference_query(session)
            if query != '':
                session.task_selection.elicitation_utterances.append(query)
            else:
                logger.warning('EMPTY REFERENCE QUERY')

        elif is_in_user_interaction(user_interaction=user_interaction,
                                    intents_list=['VagueSearchIntent']):
            query = random.choice(VAGUE_QUERIES[session.domain])
            session.task_selection.elicitation_utterances.append(query)
            
    def get_categories_by_id(self, ids) -> CategoryResults:
        
        category_ids = CategoryIDs()
        category_ids.ids.extend(ids)
        return self.searcher.retrieve_category(category_ids)

    @staticmethod
    def __update_domain(session: Session, user_interaction: InputInteraction) -> None:
        if "home improvement" in user_interaction.text.lower() or "diy" in user_interaction.text.lower():
            session.domain = Session.Domain.DIY
        elif "cooking" in user_interaction.text.lower():
            session.domain = Session.Domain.COOKING
        
    @staticmethod
    def __populate_category_choices(candidates, first_candidate_idx) -> str:
        speech_text = ''
        ordinal_phrases = [
            ["The first one is", "The second is", "And, finally"],
            ["First is", "Second is", "And, third"]
        ]
        ordinals = random.choice(ordinal_phrases)
        for ordinal_idx, candidate_idx in enumerate(range(first_candidate_idx, first_candidate_idx+3)):
            candidate = candidates[candidate_idx].category
            result = f"{candidate.title}"
            speech_text += f'{ordinals[ordinal_idx]}: {result}. '
        return speech_text
    
    @staticmethod
    def __populate_screen_with_categories(output, categories, domain) -> OutputInteraction:
        
        output.screen.format = ScreenInteraction.ScreenFormat.IMAGE_CAROUSEL 
        
        if domain == 1:
            output.screen.headline = "cooking suggestions"
        elif domain == 2:
            output.screen.headline = "DIY suggestions"
        else:
            output.screen.headline = "my suggestions"
            
        output.screen.hint_text = "more options"
            
        on_click_list = []

        for idx, category in enumerate(categories[:3]):
            image: Image = output.screen.image_list.add()
            image.path = category.category.sub_categories[0].thumbnail_url
            if image.path == "":
                image.path = category.category.sub_categories[0].candidates[0].image_url
            image.title = category.category.title
            image.description = "Our Recommendations"
            on_click_list.append(str(idx + 1))

        output.screen.on_click_list.extend(on_click_list)
        return output

    def step(self, session: Session) -> Tuple[Session, OutputInteraction]:
        """Step method for the ElicitationPolicy class.

        This method first does a safety check, then checks if the policy has been activated
        before during the current session. If it's the first call, it will return a randomly selected
        personality prompt from the data structure in schema.py. 

        On subsequent calls, it will update the elicitation utterances in the Session object and then
        generate a response 
        """

        output = OutputInteraction()
        user_interaction: InputInteraction = session.turn[-1].user_request.interaction

        logger.info(f"User Intents detected: {user_interaction.intents}")

        # SAFETY CHECK
        if is_in_user_interaction(user_interaction=user_interaction,
                                  intents_list=['DangerousQueryIntent']):
            output.speech_text = "I’m sorry, I can’t help with this type of task."
            session, output = close_session(session, output)
            set_source(output)
            return session, output

        if is_in_user_interaction(user_interaction=user_interaction,
                                  intents_list=["InformIntent"],
                                  utterances_list=["what can you do"]):
            consume_intents(user_interaction, intents_list=["VagueSearchIntent"])
            session.turn[-1].user_request.interaction.intents.append("ConfusedIntent")
            raise PhaseChangeException()

        if session.task.state.help_corner_active or "_button" in session.turn[-1].user_request.interaction.text:
            if "_button" in session.turn[-1].user_request.interaction.text and \
                    not session.task.state.help_corner_active:
                logger.info('We failed to keep session.task.state.help_corner_active. Manually rerouting...')
            logger.info('in help corner elicitation')
            if "_button" in session.turn[-1].user_request.interaction.text:
                del session.turn[-1].user_request.interaction.intents[:]
                session.turn[-1].user_request.interaction.intents.append("ConfusedIntent")
                raise PhaseChangeException()
            session.task.state.help_corner_active = False

        # OUTPUT SPEECH
        if session.task_selection.elicitation_turns == 0:
            # Entry Utterance
            sub_tree = CONVERSATION_TREE[session.domain]

            session.task.state.elicitation_personality_prompt = random.choice(sub_tree['personality_prompts'])
            output.speech_text = (
                session.task.state.elicitation_personality_prompt +
                random.choice(sub_tree['elicitation_questions'])
            )
            output.screen.hint_text = "I don't know."
            session.task_selection.elicitation_turns += 1
        else:
            # From the second interaction we are starting to update the elicitation Utterances
            self.__update_elicitation_utterances(session, user_interaction)

            turn: int = session.task_selection.elicitation_turns - 1
            response_model = CONVERSATION_TREE[session.domain]['responses']['turns'][turn]

            # Processing of the turn-specific Schema
            output.speech_text = self.__match_response_model(session, response_model)

            if output.speech_text != '':
                # If matching one of the Elicitation Turn Intents, increase the Elicitation Turns
                session.task_selection.elicitation_turns += 1
                
            else:
                
                self.__update_domain(session, user_interaction)
                
                response_model = CONVERSATION_TREE[session.domain]['responses']['general']
                # Processing of general catch-all Intents
                processed_text = self.__match_response_model(session, response_model)
                
                if processed_text == "default":
                    session.task_selection.preferences_elicited = True
                    del session.task_selection.candidates_union[:]
                    
                    output.speech_text = "How about we explore one of these topics? Select one of these, or say: " \
                                         "'more results' to view other options."
                    category_ids = [cat["id"] for cat in RECOMMENDED_CATEGORIES[session.domain]]
                    
                    category_documents = self.get_categories_by_id(category_ids)
                    
                    taskmap_category_union_list = []
                    for category_doc in category_documents.category:
                        taskmap_category_union = TaskmapCategoryUnion()
                        taskmap_category_union.category.CopyFrom(category_doc)
                        taskmap_category_union_list.append(taskmap_category_union)
                    
                    session.task_selection.candidates_union.extend(taskmap_category_union_list)
                    
                    output.speech_text += self.__populate_category_choices(session.task_selection.candidates_union,
                                                                           self.recommendations_count)
                    output = self.__populate_screen_with_categories(output, session.task_selection.candidates_union,
                                                                    session.domain)
                    set_source(output)
                    return session, output
                else:
                    output.speech_text = processed_text

        # Copy old-screen interface to keep it consistent
        output = repeat_screen_response(session, output)
        set_source(output)
        return session, output
