from taskmap_pb2 import Session, OutputInteraction, Timer, ScreenInteraction
from .abstract_intent_handler import AbstractIntentHandler
from datetime import datetime, timedelta
import dateparser
from word2number import w2n

import isodate
import pytz
from utils import logger
from typing import List


def format_delta(duration: timedelta) -> str:
    seconds = duration.seconds
    logger.info(f"Duration of timer in seconds is {seconds}")

    hours, minutes = seconds // 3600, seconds % 3600
    minutes, seconds = minutes // 60, minutes % 60

    values = [hours, minutes, seconds]
    units = "hour", "minute", "second"

    out_list = []
    for value, unit in zip(values, units):
        if value == 0:
            continue

        if value == 1:
            out_list.append(f"{value} {unit}")
        else:
            out_list.append(f"{value} {unit}s")

    return ", ".join(out_list)


def format_timer(timer: Timer) -> str:
    # Alexa uses the UTC timezone
    utc = pytz.timezone("UTC")

    expire = utc.localize(timer.expire_time.ToDatetime())
    now = datetime.now().astimezone(utc)

    og_duration = format_delta(isodate.parse_duration(timer.duration))
    remaining = format_delta(expire - now)

    if timer.state == Timer.State.RUNNING:
        response = f"One timer of {og_duration} that will expire in {remaining}. "
    else:  # PAUSED
        response = f"One timer of {og_duration} that is currently paused. "

    return response


def parse_duration(s:str) -> timedelta:
    for template in [
                        "3 quarters",
                        "three quarters",
                        "a quarter",
                        "quarter",
                        "a half",
                        "half",
                    ]:
        s = s.replace(template, "")

    tokens = s.split(" ")
    for tok in tokens:
        try:
            sub = w2n.word_to_num(tok)
        except:
            continue
        s = s.replace(tok, str(sub))

    date = dateparser.parse(s+' ago')
    if date is not None:
        delta = datetime.now().replace(microsecond=0) - date.replace(microsecond=0)
    else:
        delta = timedelta(minutes=5)

    return delta

def set_timer(s: str) -> str:
    delta = parse_duration(s)
    return isodate.duration_isoformat(delta)


class TimerHandler(AbstractIntentHandler):

    @property
    def caught_intents(self):
        return ["createTimerIntent",
                "pauseTimerIntent",
                "resumeTimerIntent",
                "deleteTimerIntent",
                "showTimerIntent"
                ]

    @staticmethod
    def __get_timer(session: Session, *enum_states: Timer.State) -> List[Timer]:
        timers = session.task.state.user_timers
        timers = [timer for timer in timers if timer.state in enum_states]

        def expired(timer):
            utc = pytz.timezone("UTC")

            expire = timer.expire_time.ToDatetime()
            # datetime given by alexa use UTC timezone
            expire = utc.localize(expire)
            now = datetime.now().astimezone(utc)
            return expire > now or timer.state == Timer.State.PAUSED

        timers = list(filter(expired, timers))
        return timers

    def step(self, session: Session) -> (Session, OutputInteraction):

        user_intents = session.turn[-1].user_request.interaction.intents
        RinD_string = session.turn[-1].user_request.interaction.params[0]
        output = OutputInteraction()

        if "createTimerIntent" in user_intents:
            # Parsing duration
            duration_str = eval(RinD_string)
            logger.info(f"Timer duration info: {duration_str}")

            output.timer.timer_id = "CreateTimerID"
            output.timer.label = "User's"
            output.timer.duration = duration_str
            output.timer.operation = Timer.Operation.CREATE
            output.timer.time.GetCurrentTime()

            output.speech_text = "I have set the timer that you requested"

        elif "pauseTimerIntent" in user_intents:
            timers = self.__get_timer(session, Timer.State.RUNNING)

            if timers:
                timer = timers[-1]
                output.timer.timer_id = timer.timer_id
                output.timer.operation = Timer.Operation.PAUSE

                output.speech_text = "The Timer has been paused"
            else:
                output.speech_text = "Sorry, there is no timer that can be paused."

        elif "resumeTimerIntent" in user_intents:
            timers = self.__get_timer(session, Timer.State.PAUSED)
            if timers:
                timer = timers[-1]
                output.timer.timer_id = timer.timer_id
                output.timer.operation = Timer.Operation.RESUME

                output.speech_text = "The Timer has been resumed"
            else:
                output.speech_text = "Sorry, there is no timer that can be resumed."

        elif "deleteTimerIntent" in user_intents:
            timers = self.__get_timer(session, Timer.State.RUNNING, Timer.State.PAUSED)
            if timers:
                timer = timers[-1]
                output.timer.timer_id = timer.timer_id
                output.timer.operation = Timer.Operation.CANCEL

                output.speech_text = "The Timer has been canceled"
            else:
                output.speech_text = "Sorry, there is no timer that can be canceled."

        elif "showTimerIntent" in user_intents:
            timers = self.__get_timer(session, Timer.State.RUNNING, Timer.State.PAUSED)

            if not timers:  # No Timers available
                output.speech_text = "You have no Timers that are set."
            else:
                output.speech_text = "I have found these timers: "

                for timer in timers:
                    output.speech_text += format_timer(timer)

        if not session.headless and len(session.turn) > 1:
            prev_screen: ScreenInteraction = session.turn[-2].agent_response.interaction.screen.SerializeToString()
            output.screen.ParseFromString(prev_screen)

        return session, output
