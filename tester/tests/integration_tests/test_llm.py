import os
import json
import time
import uuid
import random

import grpc
from google.protobuf.json_format import Parse, ParseDict, MessageToDict
import pytest

from utils import INTRO_PROMPTS, REPLACE_SUGGESTION
from taskmap_pb2 import TaskMap, Session, ConversationTurn, Task, SessionState, ReplacedIngredient
from database_pb2 import SessionRequest, TaskMapRequest
from database_pb2_grpc import DatabaseStub
from llm_pb2 import (
    MultipleSummaryGenerationRequest,
    MultipleSummaryGenerationResponse,
)
from llm_pb2_grpc import (
    LLMSummaryGenerationStub,
)

# TODO: test timeout behaviour
# TODO: test TGI being unavailable


def test_llm_chit_chat(new_session_obj, interaction_obj):
    """
    Simple test of LLM chit chat functionality.

    To trigger this code, we just create a new Session and send
    a couple of messages that will trigger the ChitChatPolicy.

    To check that the response comes from the LLM successfully
    the "source" object associated with the response needs to
    have a message that's set in the appropriate block of code
    in chitchat_policy.py
    """
    session = new_session_obj

    # start things off with a "hi"
    response = interaction_obj.run("hi", session)
    # check that this response comes from the domain_policy as expected,
    # and ends with one of the INTRO_PROMPT values
    assert response["source"]["policy"] == "domain_policy"
    interaction_obj.check_prompts(response, INTRO_PROMPTS)

    # next, reply with "what's up" - this should be classed as a ChitChatIntent and
    # trigger a call to the LLM chit chat service
    response = interaction_obj.run("what's up", session)

    # the response should now come from a particular code block in
    # chitchat_policy.py if it successfully retrieved an LLM response
    assert response["source"]["policy"] == "chitchat_policy"
    assert response["source"]["message"] == "chitchat from LLM"

    # TODO check output


@pytest.mark.slow
def test_llm_enhancement(new_session_obj, sample_taskmap_json_wikihow: str):
    """
    Tests the TaskMap enhancement performed by external_functionalities.

    Specifically this is the process triggered by loading/saving a session in
    external_functionalities/database/dynamo_db.py.

    This test sets up a minimal valid Session with a Wikihow taskmap, and deletes any
    existing copies of the TaskMap and its StagedOutput representation from the
    DynamoDB instance as a first step. This is to force the enhancement to run
    every time as normally the results are cached in the database.

    Doing this should exercise multiple different LLM components in functionalities.
    When a suitable session is loaded in DynamoDB.load_session (one which has a
    Wikihow URL and is not marked as already enhanced), it will call the enhance()
    method of the StagedEnhance class. For TaskMaps that haven't yet been enhanced,
    it spawns a thread which will end up calling LLMTaskMapEnhancer.enhance_taskmap.

    This does 2 things:
        1. It makes some llm_summary_generation requests based on groups of steps
            in the TaskMap
        2. It makes an llm_proactive_question_answering request

    i.e. both of these components are exercised by this single test.
    """

    # create the objects required
    session = new_session_obj
    taskmap = TaskMap()
    channel = grpc.insecure_channel(os.environ["EXTERNAL_FUNCTIONALITIES_URL"])
    db = DatabaseStub(channel)

    # parse the TaskMap JSON into a protobuf
    Parse(sample_taskmap_json_wikihow, taskmap)

    # construct a protobuf Session object from the basic JSON representation in "session"
    # and copy in the sample TaskMap
    session_proto = Session()
    ParseDict(session, session_proto)
    session_proto.task.taskmap.CopyFrom(taskmap)

    # construct a SessionRequest to make an RPC to external_functionalities
    session_request: SessionRequest = SessionRequest()
    session_request.id = session["session_id"]
    session_request.session.CopyFrom(session_proto)

    # delete any stored copies of the TaskMap and its StagedOutput (enhanced) representation
    taskmap_request = TaskMapRequest()
    taskmap_request.id = taskmap.taskmap_id
    db.delete_taskmap(taskmap_request)
    db.delete_stagedoutput(taskmap_request)

    # save the new session and then load it to trigger the enhancement
    # (saving will also trigger some enhancement, but not the full process)
    db.save_session(session_request)
    session = db.load_session(session_request)

    # because the database object spawns a worker thread on the remote side,
    # the RPC will return immediately. wait here until reloading the session
    # shows it marked as enhanced (via session.task.state.enhanced == True),
    # or we timeout. Repeated calls to load_session won't trigger repeated
    # enhancement requests so this is OK to do.
    timeout = 60
    delay = 10
    enhanced = False
    while not enhanced and timeout > 0:
        time.sleep(delay)
        timeout -= delay
        session = db.load_session(session_request)
        enhanced = session.task.state.enhanced

    assert enhanced


def test_llm_ingredient_substitution_step_text(interaction_obj, sample_taskmap_json_seriouseats: str):
    """
    Tests the llm_ingredient_substitution step rewriting functionality.

    This can be triggered by orchestrator/policy/validation_policy/validation_policy.py
    in certain conditions:
        - the session.task.phase must be Task.TaskPhase.VALIDATING (to trigger the policy)
        - session.task.state.requirements_displayed must be True
        - session.turn[-2].user_request.interaction must contain a QuestionIntent
        - session.turn[-2].agent_response.interaction.speech_text must contain a REPLACE_SUGGESTION
        - session.turn[-1].user_request.interaction must contain a YesIntent

    If all these conditions are satisifed, a call is made to adjust_step_texts inside
    LLMIngredientStepTextRewriter.
    """

    channel = grpc.insecure_channel(os.environ["EXTERNAL_FUNCTIONALITIES_URL"])
    db = DatabaseStub(channel)
    taskmap = TaskMap()

    Parse(sample_taskmap_json_seriouseats, taskmap)
    print("ID: ", taskmap.taskmap_id)

    # make sure our TaskMap isn't already in the database
    taskmap_request = TaskMapRequest()
    taskmap_request.id = taskmap.taskmap_id
    db.delete_taskmap(taskmap_request)
    db.delete_stagedoutput(taskmap_request)

    # construct a protobuf Session object from the basic JSON representation in session
    session_proto = Session()
    session_proto.session_id = f"test_{str(uuid.uuid4())}"

    # configure the session state required to trigger this LLM functionality
    session_proto.state = SessionState.RUNNING
    session_proto.task.phase = Task.TaskPhase.VALIDATING
    session_proto.task.state.requirements_displayed = True

    # set up a replaced ingredient (this is normally done via QA policy)
    ri = ReplacedIngredient()
    ri.original.name = "chocolate"
    ri.original.amount = "30 grams"
    ri.replacement.name = "cheese"
    ri.replacement.amount = "100 grams"
    session_proto.task.taskmap.CopyFrom(taskmap)
    session_proto.task.taskmap.replaced_ingredients.append(ri)

    # need to add a turn where the user_request.interaction contains a QuestionIntent
    t1 = ConversationTurn()
    t1.user_request.interaction.intents.extend(["QuestionIntent"])
    # also need to have an ingredient mentioned in the interaction text
    t1.user_request.interaction.text = "can you replace the chocolate in this recipe?"
    t1.id = f"test_turn_{uuid.uuid4()}"

    # and the agent must respond with a REPLACE_SUGGESTION prompt
    t1.agent_response.interaction.speech_text = f"{random.choice(REPLACE_SUGGESTION)} {ri.replacement.name}"
    session_proto.turn.extend([t1])

    # the following turn should also contain a YesIntent, but that will be generated
    # by setting the appropriate user input text below

    # save the new session first, so that the orchestrator will load it
    # with the correct state when we submit the interaction request
    session_request: SessionRequest = SessionRequest()
    session_request.id = session_proto.session_id
    session_request.session.CopyFrom(session_proto)
    db.save_session(session_request)


    # working with a session via interaction_obj requires a dict
    s = MessageToDict(session_proto, including_default_value_fields=True)
    s["session_id"] = session_proto.session_id
    # use speech text that will generate a YesIntent, required to trigger the substitution
    resp = interaction_obj.run("yes ok", s)

    # check that at least one of the steps now contains our replaced ingredient
    db.save_session(session_request)
    session = db.load_session(session_request)
    found_replacement = False
    for step in session.task.taskmap.steps:
        if ri.replacement.name in step.response.screen.requirements or ri.replacement.name in step.response.speech_text:
            found_replacement = True
            break

    # TODO: currently failing, need to try with the original model
    assert found_replacement
