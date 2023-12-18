import hashlib
import json
import os
from abc import ABC, abstractmethod
from typing import Optional

import openai
import requests
from bs4 import BeautifulSoup
from requests.models import Response

from offline_pb2 import CategoryDocument, HTMLDocument
from utils import get_file_system, logger


class AbstractTaxonomyBuilder(ABC):

    def __init__(self):
        self.openai_descriptions_folder = os.path.join(get_file_system(), "offline", "openai_responses")

        if not os.path.isdir(self.openai_descriptions_folder):
            os.makedirs(self.openai_descriptions_folder)

        openai.api_key = ''  # must be filled to generate descriptions

    @staticmethod
    def get_docid(url: str):
        """ Generate document unique identifier. """
        return hashlib.md5(url.encode('utf-8')).hexdigest()


    @staticmethod
    def get_soup(url: str, html: Optional[Response] = None) -> Optional[BeautifulSoup]:
        """
        Obtains a BeautifulSoup object for the given URL.

        If the `html` parameter is an existing requests 
        response object, the BeautifulSoup object will be 
        parsed directly from that. Otherwise requests.get
        is used to retrieve the HTML. 

        Returns:
            A BeautifulSoup object for the given URL, or None on error.
        """

        if html is None:
            logger.info(f"get_soup retrieving HTML for {url}")
            try:
                html = requests.get(url)
            except Exception as e:
                logger.warning(f"get_soup failed to retrieve HTML for {url}: {e}")
                return None

        try:
            soup = BeautifulSoup(html.text, 'html.parser')
        except Exception as e:
            logger.warning(f"get_soup failed to parse HTML for {url}: {e}")
            return None

        return soup

    @staticmethod
    def clean_text(s):
        """ Standard cleaning of text. """
        s = s.replace('</li><li>', '. ')
        return s.replace('\n', ' ').replace('\t', ' ').strip() if s is not None else s

    @staticmethod
    def write_out(data):

        if not os.path.isdir(os.path.join(get_file_system(), "offline/category_data")):
            os.makedirs(os.path.join(get_file_system(), "offline/category_data"), exist_ok=True)

        with open(os.path.join(get_file_system(), "offline/category_data/cat_data.jsonl"), "w") as json_file:
            for cat in data:
                json.dump(cat, json_file)
                json_file.write('\n')

    @abstractmethod
    def build_taxonomy(self, url: str, html=None) -> CategoryDocument:
        """
        Used to build the different categories available:
        Args:
            - urls (of the categories, e.g. {"url": https://www.wikihow.com/Category:Crafts, "name": "crafts"}
        Returns:
            - a CategoryDocument in the following format (if translated to a dictionary):
                {
                    'title': '',
                    'description': '',
                    'options_available': True,
                    questions_turns
                    'sub_categories': [
                        {'title': '',
                        'candidates': [],
                        taskmap_ids
                        images
                        'thumbnail_url': ''
                        },
                       {'title': '',
                        'candidates': [''],
                        'thumbnail_url': ''
                        },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
                       {'title': '',
                        'candidates': [],
                        'thumbnail_url': ''
                        }
                    ]
                }
        """
        pass

    def parse(self, url: str, html: HTMLDocument) -> CategoryDocument:
        category_doc = self.build_taxonomy(url, html)
        if category_doc and len(category_doc.sub_categories) < 3:
            return None
        # if category_doc and category_doc.description == "": 
        #     category_doc.description = self.generate_description(category_doc.title)
        return category_doc

    def generate_description(self, title: str) -> str:
        """Matches a description to a category. If there is no available description
        for the given category, the description is generated with OpenAI"""

        prompts_file: str = os.path.join(self.openai_descriptions_folder, "category_responses.txt")

        title_prompt_dict: dict = {}

        if os.path.isfile(prompts_file):
            with open(prompts_file, "r") as fp:
                title_prompt_dict = json.load(fp)

        if title in title_prompt_dict.keys():
            return title_prompt_dict[title]

        prompt: str = f"Context: You are an Alexa Skill that helps and guides user with home improvement and cooking " \
                      f"tasks. Tasks are divided into different categories and these categories are further divided " \
                      f"into subcategories. When a subcategory is selected, tasks related to this subcategory are " \
                      f"recommended to the user. The purpose of having categories is to be able to deal with vague " \
                      f"queries such by narrowing down the search results. It is important that when a category is " \
                      f"selected, rather than a narrowed search, the user is informed that they entered a category. " \
                      f"After the opening sentences, 3 subcategories are recommended, but this is not part of the " \
                      f"opening statement!\n\nTask: When a user chooses the category '{title}' , " \
                      f"you will generate an opening statement. The initial sentence should convey the user's " \
                      f"selection in a positive and enjoyable manner. One or two sentences should follow which " \
                      f"aim to hype how great this category is, by mentioning interesting facts about it. Finally, " \
                      f"the last sentence must inform the user that there are several subcategories available " \
                      f"for them to explore. And choose from, but do not provide any examples."

        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            max_tokens=100,
            messages=[
                {"role": "system", "content": prompt}
            ])

        description: str = completion['choices'][0]['message']['content']
        title_prompt_dict[title] = description
        logger.info(f"For category '{title}' generated description: '{description}'")

        with open(prompts_file, "w") as fp:
            json.dump(title_prompt_dict, fp, indent=2)

        return description
