import os
import uuid

from waitress import serve
from flask import Flask, request
from policy import DefaultPolicy
from analytics.general.asr_parser import ASRParser

from utils import logger
from google.protobuf.json_format import MessageToDict, ParseDict

from database_pb2_grpc import DatabaseStub
from database_pb2 import SessionRequest
from asr_info_pb2 import ASRInfo
import grpc
import threading

app = Flask(__name__)
policy = DefaultPolicy()


@app.route('/run', methods=['GET', 'POST'])
def run():
    """ """
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

    response = MessageToDict(output_interaction)

    return response


@app.route('/last_response', methods=['GET', 'POST'])
def repeat_last_response():
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
def update_timers():
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
    serve(app, host='0.0.0.0', port=8000)
    # app.run(host='0.0.0.0', port=8000, debug=True)
