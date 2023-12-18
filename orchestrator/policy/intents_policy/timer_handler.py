from datetime import datetime, timedelta
from typing import List, Tuple

import dateparser
import isodate
import pytz
from word2number import w2n

from taskmap_pb2 import OutputInteraction, ScreenInteraction, Session, Timer
from utils import logger, set_source

from .abstract_intent_handler import AbstractIntentHandler


def format_delta(duration: timedelta) -> str:
    """Get a formatted string representation of a timedelta object.

    This will return a string of the form:
        "x hours, y minutes, z seconds"
    based on the number of seconds in the supplied timedelta object. 

    The string will only contain the minimum necessary number of units,
    e.g. if the number of seconds is < 3600, then the "x hours" part
    is omitted. It will also add an "s" if necessary to any of the units
    to make them plural if needed. 

    Args:
        duration (timedelta): a datetime.timedelta object

    Returns:
        str: a string representing the time span as described above
    """
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
    """Generate speech text describing a timer.

    This method is called in response to a "showTimerIntent". If the
    given timer is active, it will return a string describing the original
    timer duration and the amount of time remaining before it expires. If the
    timer has been paused, the string will describe the original duration and
    then say that the timer is currently paused. 

    Args:
        timer (Timer): an active Timer object

    Returns:
        str: text describing the timer state
    """
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


def parse_duration(s: str) -> timedelta:
    """Converts a string containing a duration into a timedelta.

    This method strips out instances of phrases/words like "a quarter" or
    "a half" from the input string, replaces words with numbers where 
    possible (e.g. "one" => "1"), and then feeds the final result into the
    dateparser.parse method as "<string> ago".

    If successful, this will return a datetime corresponding to the parsed
    time. In this case the return value is a timedelta containing the difference
    between the current time and the parsed time, with the microsecond field
    zeroed. 

    If parsing is not successful, it defaults to returning a 5 minute timedelta.    

    Args:
        s (str): a string describing a time span

    Returns:
        timedelta: a timedelta object corresponding to the input string,
        or a default 5 minute timedelta if parsing failed
    """
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
    print(s)
    date = dateparser.parse(s + ' ago')
    if date is not None:
        delta = datetime.now().replace(microsecond=0) - date.replace(microsecond=0)
    else:
        delta = timedelta(minutes=5)

    return delta


def set_timer(s: str) -> str:
    """Convert a PhaseIntentClassifier timer intent to an ISO8601 duration string.

    This method is called indirectly through the use of ``eval()`` in the ``step``
    method of this class (TODO change this?). 

    The PhaseIntentClassifier outputs a result of the form "set_timer('time span')"
    when it classifies something as a request to set a timer. So for example the
    result could be "set_timer('5 minutes')". The use of ``eval()`` on a string like
    this then results in this method being called with the parameter set to the text
    inside the parentheses in the original string.

    Once the method is called, it just passes the duration string to ``parse_duration``
    and then uses isodate to get the result in ISO8601 format.

    Args:
        s (str): a duration, e.g. "5 minutes", "30 seconds"

    Returns:
        str: an ISO8601-formatted duration, e.g. "PT5M" for "5 minutes"
    """
    delta = parse_duration(str(s))
    return isodate.duration_isoformat(delta)


class TimerHandler(AbstractIntentHandler):

    @property
    def caught_intents(self) -> List[str]:
        """Defines the set of intents handled by this class.

        Returns:
            List[str]: list of intent names
        """
        return ["createTimerIntent",
                "pauseTimerIntent",
                "resumeTimerIntent",
                "deleteTimerIntent",
                "showTimerIntent"
                ]

    @staticmethod
    def __get_timer(session: Session, *enum_states: Timer.State.ValueType) -> List[Timer]:
        """Return any timers in the given states that haven't expired yet.

        Args:
            session (Session): the current Session object
            *enum_states (Timer.State.ValueType): 1 or more Timer.State values

        Returns:
            List[Timer]: a possibly empty list of active Timers matching the state(s)
        """
        timers = session.task.state.user_timers
        timers = [timer for timer in timers if timer.state in enum_states]

        def expired(timer: Timer) -> bool:
            """Checks if a Timer has NOT expired or is paused.

            This tests if the expiration time of the given Timer is in the
            future or if the Timer is currently paused. If either of those
            tests pass, it returns True, otherwise False.

            Args:
                timer (Timer): a Timer object
            
            Returns:
                bool: True if the Timer is still active or is paused, False if not
            """
            utc = pytz.timezone("UTC")

            expire = timer.expire_time.ToDatetime()
            expire = utc.localize(expire)
            now = datetime.now().astimezone(utc)
            return expire > now or timer.state == Timer.State.PAUSED

        timers = list(filter(expired, timers))
        return timers

    def step(self, session: Session) -> Tuple[Session, OutputInteraction]:
        """Step method for the TimerHandler class.

        This method deals with the various types of TimerIntent that may be 
        generated by the system (create/pause/resume/delete/show).

        The pause/resume/delete/show_cases are all straightforward and just populate
        an OutputInteraction to return to the client. 

        The creation case is a little more complex because it retrieves the
        PhaseIntentClassifier output from the current turn and runs it through
        ``eval()``. Since this method is only done when a "createTimerIntent" is 
        detected, the classifier output should be a string of the form 
        "set_timer('5 minutes')". The result of calling ``eval()`` is then a call to 
        the ``set_timer`` method defined above with the string inside the parentheses 
        passed as its parameter. 

        Args:
            session (Session): the current Session object

        Returns:
            tuple(updated Session, OutputInteraction)
        """
        user_intents = session.turn[-1].user_request.interaction.intents
        RinD_string = session.turn[-1].user_request.interaction.params[0]
        output = OutputInteraction()

        if "createTimerIntent" in user_intents:
            # Parsing duration
            logger.info(f'Trying to parse "{RinD_string}"...')
            try:
                duration_str = eval(RinD_string)
                logger.info(f"Timer duration info: {duration_str}")

                output.timer.timer_id = "CreateTimerID"
                output.timer.label = "User's"
                output.timer.duration = duration_str
                output.timer.operation = Timer.Operation.CREATE
                output.timer.time.GetCurrentTime()

                output.speech_text = "I have set the timer that you requested"
            except TypeError as e:
                logger.info(f"Error in Timers. No time string detected in Rind output.")
                logger.info(e)
                output.speech_text = "Sorry, I currently can't set any timers. "

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

        set_source(output)
        return session, output
