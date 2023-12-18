from .abstract_parser import AbstractParser
from compiled_protobufs.document_pb2 import CustomDocument, Step

from utils import logger


class EpicuriousParser(AbstractParser):

    def get_title(self):
        """ Scrape Document title. """
        title_object = self.soup.find('h1')
        if title_object and title_object.get('itemprop') == 'name':
            return title_object.text.strip()

    def get_date(self):
        """ Scrape and parse Document date. """
        date_obj = self.soup.find(class_='pub-date')
        if date_obj:
            # Parse text 'June 20, 2021' to date format YYYY-MM-DD.
            try:
                return self.parse_date(date_obj.text)
            except:
                logger.info("no date")

    def get_author(self):
        """ Scrape Author. """
        author_obj = self.soup.find(class_="byline author")
        if author_obj:
            return author_obj.text.strip()

    def get_description(self):
        pass

    def get_image(self):
        """ Scrape Document descriptions. """
        """ Scrape image. """
        images = self.soup.find_all('img')
        for img in images:
            src = img.get('src')
            if src is not None:
                if 'background' in img.get('src'):
                    return img.get('srcset')

    def get_video(self):
        pass

    def get_duration_minutes_total(self):
        """ Scrape and parse duration_minutes_total. """
        total_time = 0
        details_object = self.soup.find('ul', class_='o-RecipeInfo__m-Time')
        if details_object:
            time_objects = details_object.find_all('li')
            for time in time_objects:
                minutes = self.parse_time(time)
                total_time += minutes

        return int(total_time)

    def get_tags(self):
        tag_parent = self.soup.find(class_='tags')
        tag_list = []
        if tag_parent:
            tag_objects = tag_parent.find_all('a')
            for tag_object in tag_objects:
                tag = CustomDocument.Tag()
                tag.text = tag_object.text
                tag.url = 'https://www.epicurious.com' + tag_object['href']
                tag_list.append(tag)
        return tag_list

    def get_requirements(self):
        """ Scrape RecipeDocument.required_material_total. """
        # --- Ingredients ---
        req_list = []
        for ing in self.soup.find_all('li', class_='ingredient'):
            req_list.append(ing.text.strip('\n'))
        return req_list

    def get_serves(self):
        details_object = self.soup.find(class_='summary-data')
        if details_object:
            return details_object.text.replace('Yield', '')

    def get_rating_out_100(self):
        import re
        rating_obj = self.soup.find(class_='rating')
        if rating_obj:
            decimals = re.findall(r"\d+", rating_obj.text.strip())
            if '/' in rating_obj.text and len(decimals) > 1:
                return int((int(decimals[0])/int(decimals[1]))*100)

    def get_steps(self):
        """ Scrape steps. """
        # --- Ingredients ---
        step_list = []
        for step_tag in self.soup.find_all('li', class_='preparation-step'):
            step = Step()
            text = step_tag.text.strip()
            step.text = text
            imgs = step_tag.find_all('img')
            for img in imgs:
                step.image.append(img['data-src'])
            step_list.append(step)
        return step_list
