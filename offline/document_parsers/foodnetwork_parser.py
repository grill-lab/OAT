from .abstract_parser import AbstractParser
from compiled_protobufs.document_pb2 import Step


class FoodNetworkParser(AbstractParser):
    def get_title(self):
        """ Scrape Document title. """
        title_object = self.soup.find(class_='o-AssetTitle__a-Headline')
        if title_object:
            return title_object.text.strip()

    def get_date(self):
        pass

    def get_author(self):
        """ Scrape Author. """
        author_obj = self.soup.find(class_="o-Attribution__m-Author")
        if author_obj:
            author_link = author_obj.find('a')
            if author_link:
                return author_link.text.strip()

    def get_description(self):
        pass

    def get_image(self):
        """ Scrape Document descriptions. """
        """ Scrape image. """
        image_object = self.soup.find(
            sizes='(max-width: 580px) 100vw,(min-width: 581px) and (max-width: 1024px) '
                  '685px,(min-width: 1025px) and (max-width: 1149px) 745px,820px')
        if image_object:
            return "https:" + image_object['src']

    def get_video(self):
        pass

    def get_duration_minutes_total(self):
        """ Scrape and parse duration_minutes_total. """
        total_time = 0
        details_object = self.soup.find('ul', class_='o-RecipeInfo__m-Time')
        if details_object:
            time_objects = details_object.find_all('li')
            for time in time_objects:
                minutes = self.parse_time(time.text)
                total_time += minutes

        return int(total_time)

    def get_tags(self):
        return []

    def get_requirements(self):
        """ Scrape RecipeDocument.required_material_total. """
        # --- Ingredients ---
        req_list = []
        ing_object = self.soup.find(class_='o-Ingredients__m-Body')
        if ing_object:
            # Loop of ingredient objects to add full list.
            for child in ing_object.find_all('p'):
                if child.get('class') != 'o-Ingredients__a-Ingredient--SelectAll':
                    ing_text = child.text.strip()
                    if ing_text != 'Deselect All':
                        req_list.append(ing_text)
        return req_list

    def get_serves(self):
        details_object = self.soup.find('ul', class_='o-RecipeInfo__m-Yield')
        if details_object:
            return details_object.text.replace('\n', '')

    def get_rating_out_100(self):
        # print('rating')
        # print(self.soup.find(class_='review reviewSummary'))
        pass

    def get_steps(self):
        """ Scrape steps. """
        step_list = []
        steps_object = self.soup.find(class_='o-Method__m-Body')
        if steps_object:
            for step_tag in steps_object.find('ol').find_all("li"):
                step = Step()
                text = step_tag.text.strip()
                step.text = text
                imgs = step_tag.find_all('img')
                for img in imgs:
                    step.image.append(img['data-src'])
                step_list.append(step)
        return step_list
