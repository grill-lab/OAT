from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
import hashlib
import dateutil.parser as dparser
from dateutil.parser import parserinfo
import re
from utils import logger

from offline_pb2 import KnowledgeDocument


class AbstractKnowledgeParser(ABC):

    @staticmethod
    def parse_time(time_str):
        """Method to parse the time into the correct format.
            Args:
                time_str: The malformatted time

            Returns:
                The parsed time in minutes.

        """
        class CustomParserInfo(parserinfo):
            HMS = [('h', 'hr', 'hrs', 'hour', 'hours'), ('m', 'min', 'mins', 'minute', 'minutes'),
                   ('s', 'second', 'seconds')]

        try:
            parsed_time = dparser.parse(time_str, fuzzy=True, parserinfo=CustomParserInfo())
            parsed_time_min = parsed_time.minute + parsed_time.hour * 60 + parsed_time.second / 60
            return parsed_time_min
        except:
            minutes = ('m', 'min', 'mins', 'minute', 'minutes')
            hours = ('h', 'hr', 'hrs', 'hour', 'hours')
            seconds = ('s', 'second', 'seconds')

            time_num = re.findall(r"\d+", time_str.strip())
            if time_num != []:
                final_time = 0
                time_int = int(time_num[0])
                for word in time_str.split(" "):
                    if word in minutes:
                        final_time = time_int
                    elif word in hours:
                        final_time = time_int * 60
                    elif word in seconds:
                        final_time = time_int / 60

                return final_time
            else:
                return 0

    @staticmethod
    def parse_date(date_str):
        return dparser.parse(date_str, fuzzy=True).strftime("%Y-%m-%d")

    @staticmethod
    def get_docid(url):
        """ Generate document unique identifier. """
        return hashlib.md5(url.encode('utf-8')).hexdigest()

    @staticmethod
    def clean_text(s):
        """ Standard cleaning of text. """
        s = s.replace('</li><li>', '. ')
        return s.replace('\n', ' ').replace('\t', ' ').strip() if s is not None else s

    @staticmethod
    def get_soup_object(html):
        """ Build BeautifulSoup object from HTML. """
        return BeautifulSoup(html, 'html.parser')

    @abstractmethod
    def get_title(self):
        """ Parse title. """
        pass

    @abstractmethod
    def get_date(self):
        """ Parse title. """
        pass

    @abstractmethod
    def get_author(self):
        """ Parse author. """
        pass

    @abstractmethod
    def get_contents(self, url=None):
        """ Parsing page contents """
        pass

    def parse(self, url, html):
        """  Parse HTML string. """
        doc = KnowledgeDocument()

        # Build soup from HTML string.
        self.soup = self.get_soup_object(html=html)

        doc.source_url = url

        if self.get_docid(url=url):
            doc.knowledge_id = self.get_docid(url=url)

        if self.get_title():
            doc.title = self.get_title()
        else:
            logger.info(f'No title for {url}')
            return

        content_dic = self.get_contents(url)
        contents = content_dic.get('contents', [])

        if len(contents) > 0:
            for part in contents:
                if part != "":
                    doc.contents.append(part)
        else:

            logger.info(f'No contents for {doc.source_url}')
            return

        if content_dic.get("mentioned_links"):
            for link in content_dic["mentioned_links"]:
                doc.mentioned_links.append(link)

        if content_dic.get("mentioned_tasks_ids"):
            logger.info('Mentioned recipe found!!')
            for doc_id in content_dic["mentioned_tasks_ids"]:
                doc.mentioned_tasks_ids.append(doc_id)

        if self.get_date():
            doc.date = self.get_date()

        if self.get_author():
            doc.author = self.get_author()

        return doc
