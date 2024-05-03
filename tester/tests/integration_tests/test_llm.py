import os
import json
import time
import uuid
import random

import grpc
from google.protobuf.json_format import Parse, ParseDict, MessageToDict
import pytest

from utils import INTRO_PROMPTS, REPLACE_SUGGESTION
from taskmap_pb2 import TaskMap, Session, ConversationTurn, Task, SessionState
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


def test_llm_summary_generation(sample_taskmap_json_wikihow: str):
    """
    Tests functionality for generating steps from a TaskMap.
    """

    # TODO: adapt this to trigger the actual code like the other tests

    # parse the raw JSON sample taskmap into a TaskMap object
    taskmap = TaskMap()
    Parse(sample_taskmap_json_wikihow, taskmap)

    functionalities_channel = grpc.insecure_channel(os.environ["FUNCTIONALITIES_URL"])
    llm_summary_stub = LLMSummaryGenerationStub(functionalities_channel)

    # this code is a slightly modified version of LLMTaskMapEnhancer.enhance_taskmap from
    # external_functionalities. it loads an example TaskMap instance and constructs and
    # sends a summarisation request to exercise the llm_summary_generation path
    steps = taskmap.steps
    grouped_steps = [steps[i : i + 3] for i in range(0, len(steps), 3)]

    for group in grouped_steps:
        request: MultipleSummaryGenerationRequest = MultipleSummaryGenerationRequest()
        for step in group:
            request.task_title.append(taskmap.title)
            request.step_text.append(step.response.speech_text)
            request.more_details.append(step.response.description)
        summaries: MultipleSummaryGenerationResponse = llm_summary_stub.generate_summaries(request)
        for i, step in enumerate(group):
            step.response.speech_text = summaries.summary[i]

    # TODO check output


def test_llm_chit_chat(new_session_obj, interaction_obj):
    session = new_session_obj

    # start things off with a "hi"
    response = interaction_obj.run("hi", session)
    # check that this response comes from the domain_policy as expected, and ends with one of the
    # INTRO_PROMPT values
    assert response["source"]["policy"] == "domain_policy"
    interaction_obj.check_prompts(response, INTRO_PROMPTS)

    # next, reply with "what's up" - this should be classed as a ChitChatIntent and
    # trigger a call to the LLM chit chat service
    response = interaction_obj.run("what's up", session)
    # the response should now come from a particular line in chitchat_policy.py if
    # it successfully retrieved an LLM response
    assert response["source"]["policy"] == "chitchat_policy"
    assert response["source"]["lineNumber"] == 152

    # TODO check output


@pytest.mark.slow
def test_llm_enhancement(new_session_obj, sample_taskmap_json_wikihow: str):
    """
    Tests the TaskMap enhancement performed by external_functionalities.

    This should exercise both the llm_description_generation and 
    llm_proactive_question_generation gRPC services in functionalities.

    Normally this is triggered by loading a session with a non-enhanced TaskMap.
    After a TaskMap has been enhanced it's saved to a database so it doesn't get
    enhanced again. To make this work in a repeatable way, this test loads the same
    sample TaskMap but overwrites its "taskmap_id" field with a new value each time.

    An additional problem is that the enhancement is triggered by loading an existing
    session. To workaround this, the test creates a minimal valid Session, saves it,
    then performs a load to start the enhancement process.
    """
    session = new_session_obj
    taskmap = TaskMap()
    Parse(sample_taskmap_json_wikihow, taskmap)

    # construct a protobuf Session object from the basic JSON representation in "session"
    # and copy in the sample TaskMap
    session_proto = Session()
    ParseDict(session, session_proto)
    session_proto.task.taskmap.CopyFrom(taskmap)

    # construct a SessionRequest for an RPC to external_functionalities
    session_request: SessionRequest = SessionRequest()
    session_request.id = session["session_id"]
    session_request.session.CopyFrom(session_proto)

    channel = grpc.insecure_channel(os.environ["EXTERNAL_FUNCTIONALITIES_URL"])
    db = DatabaseStub(channel)

    # make sure this TaskMap isn't already in the database
    taskmap_request = TaskMapRequest()
    taskmap_request.id  = taskmap.taskmap_id
    db.delete_taskmap(taskmap_request)

    # save the new session and then load it to trigger the enhancement
    db.save_session(session_request)
    session = db.load_session(session_request)

    # because the database object spawns a worker thread on the remote side,
    # the RPC will return immediately. wait here until reloading the session
    # shows it marked as enhanced (via session.task.state.enhanced == True),
    # or we timeout
    timeout = 30
    delay = 5
    enhanced = False
    while not enhanced and timeout > 0:
        time.sleep(delay)
        timeout -= delay
        session = db.load_session(session_request)
        enhanced = session.task.state.enhanced

    assert enhanced


def test_llm_ingredient_substitution_step_text(interaction_obj, sample_taskmap_json_wikihow: str):
    # this functionality is called from orchestrator/policy/validation_policy/validation_policy.py

    # it looks like what we need to trigger this is:
    # session.task.phase = Task.TaskPhase.VALIDATING (to trigger ValidationPolicy)
    # then in ValidationPolicy, the conditions necessary to hit the rewriter are:
    # 1. session.task.state.requirements_displayed = True
    # 2. session.turn[-2].user_request.interaction contains a QuestionIntent
    # 3. session.turn[-2].agent_response.interaction.speech_text contains any REPLACE_SUGGESTION
    # 4. session.turn[-1].user_request.interaction contains a YesIntent

    taskmap = TaskMap()
    Parse(sample_taskmap_json_wikihow, taskmap)

    # construct a protobuf Session object from the basic JSON representation in session
    session_proto = Session()
    session_proto.session_id = f"test_{str(uuid.uuid4())}"

    # configure the rest of the session state required
    session_proto.state = SessionState.RUNNING
    session_proto.task.phase = Task.TaskPhase.VALIDATING
    session_proto.task.state.requirements_displayed = True

    # need to add a turn where the user_request.interaction contains a QuestionIntent
    t1 = ConversationTurn()
    t1.user_request.interaction.intents.extend(["QuestionIntent"])
    t1.id = f"test_turn_{uuid.uuid4()}"

    # and the agent must respond with a REPLACE_SUGGESTION prompt
    t1.agent_response.interaction.speech_text = random.choice(REPLACE_SUGGESTION)
    session_proto.turn.extend([t1])

    # the following turn should also contain a YesIntent, but that will be generated
    # by setting the appropriate user input text below

    # save the new session first, so that the orchestrator will load it
    # with the correct state when we submit the interaction request
    session_request: SessionRequest = SessionRequest()
    session_request.id = session_proto.session_id
    session_request.session.CopyFrom(session_proto)
    channel = grpc.insecure_channel(os.environ["EXTERNAL_FUNCTIONALITIES_URL"])

    db = DatabaseStub(channel)
    db.save_session(session_request)

    # make sure this TaskMap isn't already in the database
    taskmap_request = TaskMapRequest()
    taskmap_request.id  = taskmap.taskmap_id
    db.delete_taskmap(taskmap_request)

    s = MessageToDict(session_proto, including_default_value_fields=True)

    # use speech text that will generate a YesIntent, required to trigger the substitution
    s["session_id"] = session_proto.session_id
    resp = interaction_obj.run("yes ok", s)

    # TODO: the problem with this is it finds nothing to do with the current sample taskmap, need to try some others


def test_llm_ingredient_substitution_2():
    # see functionalities/qa/composed_qa.py
    pass
