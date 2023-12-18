from exceptions import PhaseChangeException
from policy.abstract_policy import AbstractPolicy
from taskmap_pb2 import Session, SessionState, Task
from utils import logger


class ResumingPolicy(AbstractPolicy):

    @staticmethod
    def __reset_session(session: Session) -> None:
        """'Resets' a Session object by clearing most of the state.

        This method will 'reset' a Session object by creating a new
        empty Session, copying over the .session_id and .greetings fields
        from the original, copying over the list of turn objects, and then
        overwriting the original object with the new one. This will have
        the effect of resetting the values of all the other fields in the
        final Session to their defaults.

        Args:
            session (Session): the current Session object

        Returns:
            Nothing
        """
        session_id = session.session_id
        new_session = Session()
        new_session.session_id = session_id

        for turn in session.turn:
            new_turn = new_session.turn.add()
            new_turn.ParseFromString(turn.SerializeToString())

        new_session.greetings = session.greetings
        session.ParseFromString(new_session.SerializeToString())

    def step(self, session: Session) -> None:
        """Step method for the ResumingPolicy class.

        This method will only be called by PhasedPolicy if the session's .state field
        (not task phase!) is NOT set to SessionState.RUNNING. Triggering this method
        means that a previously closed session has been reloaded from the database.

        session.state = SessionState.RUNNING

        If the session's resume_task field is False, the __reset_session method is
        called to reset much of the session's state (meaning that this is a returning
        user starting a fresh interaction rather than resuming an in-progress one).

        If the session's task phase is DOMAIN/PLANNING/CLOSING/VALIDATING, then
        __reset_session is also called to reset the state.

        Finally, the method will update the .state field to SessionState.RUNNING, add
        a "RepeatIntent" to the most recent turn, and then trigger a PhaseChangeException.
        The result of this should be to cause the next policy to be activated to repeat
        its last response/instruction to help the user pick up where they left off.

        Args:
            session (Session): the current Session object

        Returns:
            Nothing (raise PhaseChangeException)
        """
        session.state = SessionState.RUNNING

        if not session.resume_task:
            self.__reset_session(session)
            logger.info('USER HAS USED BOT BEFORE, BUT RESUME_TASK IS FALSE')
            raise PhaseChangeException()

        # If taskmap is set it means that we were in execution when we did exit the previous time
        if session.task.taskmap.title != "":
            session.task.phase = Task.TaskPhase.EXECUTING
            session.turn[-1].user_request.interaction.intents.append("RepeatIntent")
            raise PhaseChangeException()

        # reset if not in going back to Execution Phase
        else:
            self.__reset_session(session)
            raise PhaseChangeException()
