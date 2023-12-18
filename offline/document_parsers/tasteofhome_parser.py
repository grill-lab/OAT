import json
import re

from .abstract_parser import AbstractParser
from compiled_protobufs.document_pb2 import CustomDocument, Step


class TasteOfHomeParser(AbstractParser):
    script = {}

    def get_script(self):
        script = self.soup.find_all('script')
        for scr in script:
            if scr.get('type') == 'application/ld+json' and '"@type": "Recipe"' in scr.text:
                self.script = json.loads(scr.text)

    def get_title(self):
        """ Scrape Document title. """
        title_object = self.soup.find(class_='recipe-title')
        if title_object:
            return title_object.text.strip()

    def get_date(self):
        pass

    def get_author(self):
        self.get_script()
        """ Scrape Author. """
        author_obj = self.script.get('author')
        if author_obj:
            return author_obj['name']

    def get_description(self):
        """ Scrape Document descriptions. """
        notes = self.script.get('description')
        if notes:
            return notes

    def get_image(self):
        """ Scrape image. """
        image_parent = self.script.get('image')
        if image_parent:
            if len(image_parent) > 0:
                return image_parent[0]

    def get_video(self):
        pass

    def get_duration_minutes_total(self):
        """ Scrape and parse duration_minutes_total. """
        details_text = self.soup.find(class_='recipe-time-yield__label-prep')
        if details_text:
            time_num = re.findall(r"\d+", details_text.text.strip())
            if len(time_num) > 1:
                total_time = 0
                for time in time_num:
                    total_time += int(time)
                return int(total_time)
            else:
                return int(self.parse_time(details_text.text))

    def get_tags(self):
        tag_list = []
        category = self.script.get('recipeCategory')
        if category:
            for cat in category:
                tag = CustomDocument.Tag()
                tag.text = cat
                tag_list.append(tag)
        cuisine = self.script.get('recipeCuisine')
        if cuisine:
            tag = CustomDocument.Tag()
            tag.text = cuisine
            tag_list.append(tag)
        return tag_list

    def get_requirements(self):
        """ Scrape RecipeDocument.required_material_total. """
        req_list = []
        # --- Ingredients ---
        ing_object = self.script.get('recipeIngredient')
        if ing_object:
            for ing in ing_object:
                req_list.append(ing)
        return req_list

    def get_serves(self):
        details_object = self.script.get('recipeYield')
        if details_object:
            return details_object

    def get_rating_out_100(self):
        ranking_object = self.soup.find(class_='rating')
        # Taste of home rates recipes out of 5 stars based on comments.
        # Each star can either be 'dashicons-star-filled' (20), 'dashicons-star-half' (10), 'dashicons-star-empty' (0).
        if ranking_object:
            # Loop over stars objects.
            ranking_out_100 = 0
            for star in ranking_object.find_all('i'):
                star_class = star.get('class')
                if star_class:
                    star_class = star_class[-1]
                    if star_class == 'dashicons-star-filled':
                        ranking_out_100 += 20
                    elif star_class == 'dashicons-star-half':
                        ranking_out_100 += 10
                    elif star_class == 'dashicons-star-empty':
                        ranking_out_100 += 0
                    else:
                        # Be safe extraction team!
                        return

            return int(ranking_out_100)

    def get_steps(self):
        """ Scrape steps. """
        step_list = []
        steps_object = self.soup.find(class_='recipe-directions__list')
        if steps_object:
            for step_tag in steps_object.find_all("li"):
                step = Step()
                text = step_tag.text.strip()
                step.text = text
                imgs = step_tag.find_all('img')
                for img in imgs:
                    step.image.append(img['data-src'])
                step_list.append(step)
        return step_list