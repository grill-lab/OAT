import os
from datetime import datetime

import pytz
import requests
import uuid


class InteractionHelper:

    def __init__(self):
        pass

    def get_speech_text(self, response: dict) -> str:
        """
        Given a response dict, extract and return the speech text content.

        Args:
            response: a JSON dict as returned by the `run` method

        Returns:
            A string containing the extracted text
        """
        pass

    def is_closed(self, response: dict) -> bool:
        """
        Given a response dict, check if its session has closed/finished.

        Args:
            response: a JSON dict as returned by the `run` method

        Returns:
            True if the session is closed, False otherwise
        """
        return response.get('shouldEndSession', False)

    def get_transcript(self, response: dict):
        """
        Given a response dict, return a transcript of the interaction(?).

        Args:
            response: a JSON dict as returned by the `run` method

        Returns:
            A transcript if available (TODO type?) or None otherwise
        """
        return response.get('card', None)

    def run(self, input_text: str, session: dict, intent: str = '') -> dict:
        """
        Perform a single query/response interaction with the system.

        Relies on the `send_request` method.

        Args:
            input_text: text to be sent to the system (str)
            session: current session state (dict)
            intent: an intent to pass along with the text (str, may be empty)

        Returns:
            a JSON dict generated from the HTTP response
        """
        pass

    def send_request(self, input_text: str, session_id: str, is_headless: bool, intent: str) -> requests.Response:
        """
        Send an HTTP request to the system and receive a response.

        Args:
            input_text: text to be sent to the sytem (str)
            session_id: session identifier (str)
            is_headless: True to indicate a headless device, False otherwise (bool)
            intent: an intent to pass along with the text (str, may be empty)

        Returns:
            a requests.Response object
        """
        pass

    def check_prompts(self, response_text: str, prompts: [], num: int = 0) -> None:
        """Helper method for running asserts on responses."""

        # catch any cases where a single string is passed instead
        if isinstance(prompts, str):
            prompts = [prompts]

        if num > 0:
            assert [prompt in self.get_speech_text(response_text) for prompt in prompts].count(True) == num
        else:
            assert any(prompt in self.get_speech_text(response_text) for prompt in prompts)

    def format_option_coref(self, option_number, response):
        speech_text = self.get_speech_text(response)
        sentences = speech_text.split('. ')[1:-1]
        # in case we have an acknoledgement
        if len(sentences[0].split(": ")) == 1:
            options = [sentence.split(': ')[1] for sentence in sentences[1:]]
        else:
            options = [sentence.split(': ')[1] for sentence in sentences]
        coref_option = options[option_number - 1]
        if " by" in coref_option:
            return coref_option.split(" by")[0]
        return coref_option


class OATInteractionHelper(InteractionHelper):

    def __init__(self):
        pass

    def get_speech_text(self, response: dict) -> str:
        """
        Given a response dict, extract and return the speech text content.

        Args:
            response: a JSON dict as returned by the `run` method

        Returns:
            A string containing the extracted text
        """
        return response['speechText']

    def run(self, input_text: str, session: dict, intent: str = '') -> dict:
        """
        Perform a single query/response interaction with the system.

        Relies on the `send_request` method.

        Args:
            input_text: text to be sent to the system (str)
            session: current session state (dict)
            intent: an intent to pass along with the text (str, may be empty)

        Returns:
            a JSON dict generated from the HTTP response
        """
        response = self.send_request(input_text, intent, session['id'], session['headless'])
        response_json = response.json()
        print(f'USER: {input_text}')
        try:
            print(f'OAT-BOT: {self.get_speech_text(response_json)}')
        except:
            pass
        return response_json

    def send_request(self, input_text: str, intent: str, session_id: str, is_headless: bool) -> requests.Response:
        """
        Send an HTTP request to the system and receive a response.

        Args:
            input_text: text to be sent to the sytem (str)
            session_id: session identifier (str)
            is_headless: True to indicate a headless device, False otherwise (bool)
            intent: an intent to pass along with the text (str, may be empty)

        Returns:
            a requests.Response object
        """
        url = os.environ['DISTRIBUTOR_URL'] + '/run'

        if session_id == '':
            session_id = 'Testing ID'

        request = {
            'id': session_id,
            'headless': is_headless,
            'intent': {
                'name': intent,
                'slots': {
                    'text': {
                        'name': 'text',
                        'value': input_text,
                    }
                }
            },
            'resume_task': True,
            'wait_save': True,
            'asr_info': {},
            'list_permissions': False,
            'text': input_text,
        }

        response = requests.post(url, json=request, timeout=10)
        return response
