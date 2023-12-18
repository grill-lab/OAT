import os
import threading
import uuid

import grpc
from flask import Flask, request
from google.protobuf.json_format import MessageToDict, ParseDict
from waitress import serve

from asr_info_pb2 import ASRInfo
from database_pb2 import SessionRequest
from database_pb2_grpc import DatabaseStub
from policy import DefaultPolicy
from utils import logger, log_latency


"""This module receives client requests and sends back system responses.

The orchestrator implements the OAT API used by external clients. It's a simple
Flask application which exposes 3 endpoints:
    - run (receive a client request and send back a system response)
    - last_response (repeat the last response from a session)
    - update_timers (update/add timers in a session)

The work of generating a system response is the responsibility of the policy 
package. The ``run`` method calls the ``PhasedPolicy.step`` method, and this in
turn will call other lower level policies until a response is generated and 
bubbles back up to the orchestrator. 

System responses are instances of the ``OutputInteraction`` proto serialized to JSON.
"""


app = Flask(__name__)
policy = DefaultPolicy()

@app.route('/run', methods=['GET', 'POST'])
@log_latency
def run() -> dict:
    """Main client endpoint for the OAT system.

    This method is the Flask handler for the /run endpoint, used by clients to
    interact with OAT. It expects to receive a JSON request body containing things
    like a client ID, client text, etc.

    The client ID is used to create or retrieve a Session object from the database 
    service before passing this on to the DefaultPolicy class (an instance of 
    PhasedPolicy in the current system).

    After the necessary policy step(s) have been executed, the Session is updated
    and stored back in the OAT database, and a JSON representation of an 
    OutputInteraction proto is returned to the client.

    Args:
        none (JSON data accessed via the Flask "request" object)

    Returns:
        JSON copy of an OutputInteraction object
    """
    channel = grpc.insecure_channel(os.environ['EXTERNAL_FUNCTIONALITIES_URL'])
    db = DatabaseStub(channel)

    session_request: SessionRequest = SessionRequest()
    session_request.id = request.json['id']

    logger.info("Calling DB to load session.")
    session = db.load_session(session_request)
    logger.info("Session loaded.")

    resume_task = request.json.get('resume_task', None)
    logger.info(f'RESUME TASK FLAG IS SET TO {resume_task}')
    if resume_task is None:
        session.resume_task = True
    else:
        session.resume_task = resume_task

    has_list_permissions = request.json.get('list_permissions', False)
    session.has_list_permissions = has_list_permissions
    asr_message = ParseDict(request.json.get('asr_info', {}), ASRInfo())
    headless = request.json.get('headless', 'true')

    if not isinstance(headless, bool):
        if headless == 'true':
            session.headless = True
        else:
            session.headless = False
    else:
        session.headless = headless

    # POPULATING NEW USER TURN
    new_turn = session.turn.add()
    new_turn.id = "turn_" + str(uuid.uuid4())
    new_turn.user_request.interaction.text = request.json['text'] or ''

    intents = request.json.get('intents', []) or []
    new_turn.user_request.interaction.intents.extend(intents)
    new_turn.user_request.time.GetCurrentTime()  # this method actually populates the object with the current time
    new_turn.user_request.interaction.asr_info.CopyFrom(asr_message)

    if "general" in intents:
        new_turn.user_request.interaction.intents.remove("general")

    logger.info("Calling policy step.")
    try:
        session, output_interaction = policy.step(session)
    except Exception as e:
        logger.error("Error executing Policy", exc_info=e)
        raise e

    session.turn[-1].agent_response.interaction.ParseFromString(output_interaction.SerializeToString())
    session.turn[-1].agent_response.time.GetCurrentTime() # this method populates the object with the current time

    # Re-using session_request that already contains the correct ID for convenience
    session_request.session.ParseFromString(session.SerializeToString())

    def save_session():
        db.save_session(session_request)

    if request.json.get('wait_save', False):
        save_session()
    else:
        thread = threading.Thread(target=save_session)
        thread.start()

    if len(output_interaction.source.policy) == 0:
        logger.warning('MISSING POLICY SOURCE')
    response = MessageToDict(output_interaction)

    return response


@app.route('/last_response', methods=['GET', 'POST'])
@log_latency
def repeat_last_response() -> dict:
    """Return the most recent system respones for the given session ID.

    This method uses the supplied ID to retrieve a session from the database,
    then simply returns the last OutputInteraction from the list of turns. 

    Args:
        none (JSON data accessed via the Flask "request" object)

    Returns:
        JSON copy of an OutputInteraction object
    """
    channel = grpc.insecure_channel(os.environ['EXTERNAL_FUNCTIONALITIES_URL'])
    db = DatabaseStub(channel)

    session_request: SessionRequest = SessionRequest()
    session_request.id = request.json['id']

    logger.info("Calling DB to load session.")
    session = db.load_session(session_request)
    logger.info("Session loaded.")

    output_interaction = session.turn[-1].agent_response.interaction
    response = MessageToDict(output_interaction)

    return response


@app.route('/update_timers', methods=['GET', 'POST'])
@log_latency
def update_timers() -> dict:
    """Add/update timers for a session.

    This method expects to receive a JSON body with a 'timers' field containing
    a list of ``Timer`` protos. Any existing timers in the session already are
    removed and the ``.user_timers`` field is updated to match the new list 
    before the session is saved. 

    Args:
        none (JSON data accessed via the Flask "request" object)

    Returns:
        Empty JSON blob
    """
    channel = grpc.insecure_channel(os.environ['EXTERNAL_FUNCTIONALITIES_URL'])
    db = DatabaseStub(channel)

    session_request: SessionRequest = SessionRequest()
    session_request.id = request.json['id']
    session = db.load_session(session_request)

    del session.task.state.user_timers[:]

    timers_dict_list = request.json['timers']
    for timer_dict in timers_dict_list:
        timer = session.task.state.user_timers.add()
        ParseDict(timer_dict, timer)

    session_request.session.ParseFromString(session.SerializeToString())
    db.save_session(session_request)

    logger.info("Updated the Timers inside the session")

    return {}


if __name__ == "__main__":
    logger.info("Orchestrator will run on port 8000")
    serve(app,
          host='0.0.0.0',
          port=8000,
          threads=64,
          backlog=64,
          channel_timeout=10,
          cleanup_interval=10,
          connection_limit=196)
    # app.run(host='0.0.0.0', port=8000, debug=True)
