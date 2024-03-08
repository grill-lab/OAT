from typing import Optional, List

from bs4 import Tag

from .abstract_parser import AbstractParser
from compiled_protobufs.document_pb2 import Step, CustomDocument


class AllRecipesParser(AbstractParser):
    def get_title(self) -> Optional[str]:
        """Get the title of the recipe"""
        title_element = self.soup.find(class_="article-heading type--lion")
        if title_element is not None:
            return self.clean_text(title_element.text)

    def get_date(self) -> Optional[str]:
        """Get the date the recipe was created/updated"""
        date_element = self.soup.find(class_="mntl-attribution__item-date")
        if date_element is not None:
            date_text = self.clean_text(date_element.text)
            # format is "Updated on August 24, 2023"
            # can just pass this to self.parse_date, which uses fuzzy parsing
            return self.parse_date(date_text)

    def get_author(self) -> Optional[str]:
        """Get the name of the author"""
        name_element = self.soup.find(class_="mntl-attribution__item-name")
        if name_element is not None:
            name_text = self.clean_text(name_element.text)
            return name_text

    def get_description(self) -> Optional[str]:
        """Get the short description of the recipe from the header block"""
        desc_element = self.soup.find(class_="article-subheading type--dog")
        if desc_element is not None:
            desc_text = self.clean_text(desc_element.text)
            return desc_text

    def get_image(self) -> Optional[str]:
        """Get the URL of the main recipe image"""
        img_element = self.soup.find(class_="primary-image__image")
        if img_element is not None:
            img_url = img_element.get("src", None)
            return img_url

    def get_video(self) -> Optional[str]:
        """Get video URL, if any (ignoring this here)"""
        return None

    def get_duration_minutes_total(self) -> Optional[int]:
        """Get the total time required for the recipe (prep+cooking)"""
        recipe_details_elements = self.soup.find_all(class_="mntl-recipe-details__item")
        for recipe_detail_element in recipe_details_elements:
            children = list(
                filter(lambda x: isinstance(x, Tag), recipe_detail_element.children)
            )
            if children[0].text == "Total Time:":
                # format is "x mins", or "x hr, y mins"
                duration_text = children[1].text.split(" ")
                hours, mins = 0, 0

                if "hr" in duration_text[1]:
                    hours = int(duration_text[0])
                    mins = int(duration_text[2])
                else:
                    mins = int(duration_text[1])
                    
                duration_mins = (hours * 60) + mins
                return duration_mins

    def get_tags(self) -> List[CustomDocument.Tag]:
        return []

    def get_requirements(self) -> List[str]:
        requirements = []

        ingredients_list = self.soup.find(class_="mntl-structured-ingredients__list")
        if ingredients_list is not None:
            for element in ingredients_list:
                if isinstance(element, Tag):
                    requirements.append(self.clean_text(element.text))

        return requirements

    def get_serves(self) -> Optional[str]:
        """Get the number of servings in the recipe"""
        recipe_details_elements = self.soup.find_all(class_="mntl-recipe-details__item")
        for recipe_detail_element in recipe_details_elements:
            children = list(
                filter(lambda x: isinstance(x, Tag), recipe_detail_element.children)
            )
            if children[0].text == "Servings:":
                servings = children[1].text
                return servings

    def get_rating_out_100(self) -> Optional[int]:
        """Get recipe rating score"""
        rating_element = self.soup.find(class_="mntl-recipe-review-bar__rating")
        if rating_element is not None:
            # this gives the score out of 5, e.g. "4.3"
            orig_rating = float(rating_element.text)

            # scale up to 0-100
            rating = orig_rating * 20

            return int(rating)

    def get_steps(self) -> List[Step]:
        """Get the recipe steps list"""
        steps = []
        steps_elements = self.soup.find_all(class_="mntl-sc-block-group--LI")

        for step_element in steps_elements:
            text_element = step_element.find("p")
            if text_element is not None:
                text = self.clean_text(text_element.text)
                step = Step()
                step.text = text
                # can add image here via step.image.append(url)
                steps.append(step)

        return steps


if __name__ == "__main__":
    import urllib.request

    url = "https://www.allrecipes.com/recipe/212498/easy-chicken-and-broccoli-alfredo/"
    html = urllib.request.urlopen(url).read().decode()
    AllRecipesParser().parse(url, html)
