import json

from .abstract_parser import AbstractParser
from document_pb2 import Step, CustomDocument


class WholeFoodsParser(AbstractParser):

    def __get_schema(self):
        """ get schema.org json"""
        schema = self.soup.find_all('script', attrs={"type": "application/ld+json"})
        if schema:
            if len(schema) > 0:
                return json.loads(schema[0].string)

    def get_title(self):
        """ Parse title. """
        title = self.soup.find(class_='w-header-title')
        if title:
            return self.clean_text(title.text)

    def get_image(self):
        """ Parse image url. """
        schema = self.__get_schema()
        if schema:
            if schema.get('image'):
                return schema.get('image')[0]

    def get_author(self):
        pass

    def get_tags(self):
        tag_object = self.soup.find(class_='w-content-special-diets')
        tag_list = []
        if tag_object:
            tags = tag_object.find(class_='w-diet-text')
            for t in tags:
                new_tag = CustomDocument.Tag()
                new_tag.text = t.string
                tag_list.append(new_tag)
        return tag_list

    def get_requirements(self):
        """ Parse requirements. """
        schema = self.__get_schema()
        requirements_list = []
        if schema:
            if schema.get('recipeIngredient'):
                for r in schema.get('recipeIngredient'):
                    requirements_list.append(r)
        return requirements_list

    def get_steps(self):
        """ Parse steps. """
        schema = self.__get_schema()
        step_list = []
        if schema:
            if schema.get('recipeInstructions'):
                for r in schema.get('recipeInstructions'):
                    step = Step()
                    step.text = r.get('text')
                    step_list.append(step)     
        return step_list

    def get_date(self):
        schema = self.__get_schema()
        if schema:
            if schema.get('datePublished'):
                return schema.get('datePublished')

    def get_description(self):
        """ Parse descriptions. """
        schema = self.__get_schema()
        if schema:
            if schema.get('description', '') != '':
                text = schema['description']
                return text

    def get_video(self):
        pass

    def get_duration_minutes_total(self):
        schema = self.__get_schema()
        if schema:
            if schema.get('totalTime', '') != '':
                text = schema['totalTime']
                return int(self.parse_time(text))

    def get_serves(self):
        schema = self.__get_schema()
        if schema:
            if schema.get("recipeYield", '') != '':
                return schema["recipeYield"]

    def get_rating_out_100(self):
        pass
