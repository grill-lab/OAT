from .abstract_parser import AbstractParser
from compiled_protobufs.document_pb2 import CustomDocument, Step


class Food52Parser(AbstractParser):
    def get_title(self):
        """ Scrape Document title. """
        title_object = self.soup.find(class_='recipe__title')
        if title_object:
            return title_object.text.strip()

    def get_date(self):
        """ Scrape and parse Document date. """
        date_obj = self.soup.find(class_='meta__date')
        if date_obj:
            # Parse text 'June 20, 2021' to date format YYYY-MM-DD.
            return self.parse_date(date_obj.text)

    def get_author(self):
        """ Scrape Author. """
        author_obj = self.soup.find(class_="meta__caps")
        if author_obj:
            return author_obj.text.strip()
        else:
            author_obj = self.soup.find(class_="meta__author")
            if author_obj:
                return author_obj.text.strip()

    def get_description(self):
        """ Scrape Document descriptions. """
        description = ''
        # Recipe notes.
        notes = self.soup.find(class_='recipe__notes')
        if notes:
            for note in notes.find_all('p'):
                description += note.text.strip()

        return description

    def get_image(self):
        """ Scrape image. """
        image_parent = self.soup.find(id='recipeCarouselRoot')
        if image_parent:
            image_object = self.soup.find('img')
            if image_object:
                return image_object['data-pin-media']

    def get_video(self):
        pass

    def get_duration_minutes_total(self):
        """ Scrape and parse duration_minutes_total. """
        total_time = 0
        details_object = self.soup.find('ul', class_='recipe__details')
        if details_object:
            time_objects = details_object.find_all('li')
            if time_objects:
                if len(time_objects) == 3:
                    prep_time = time_objects[0]
                    cooking_time = time_objects[1]
                    if prep_time:
                        prep_time = prep_time.text
                        prep_time_min = self.parse_time(prep_time)
                        total_time += prep_time_min
                    if cooking_time:
                        cooking_time = cooking_time.text
                        cooking_time_min = self.parse_time(cooking_time)
                        total_time += cooking_time_min

        return int(total_time)

    def get_tags(self):
        tag_parent = self.soup.find(class_='tag-list')
        tag_list = []
        if tag_parent:
            tag_objects = tag_parent.find_all('a')
            for tag_object in tag_objects:
                tag = CustomDocument.Tag()
                tag.text = tag_object.text
                tag.url = tag_object['href']
                tag_list.append(tag)
        return tag_list

    def get_requirements(self):
        """ Scrape RecipeDocument.required_material_total. """
        # --- Ingredients ---
        req_list = []
        ing_object = self.soup.find(class_='recipe__list--ingredients')
        if ing_object:
            # Loop of ingredient objects to add full list.
            for child in ing_object.find_all('li'):
                if child.get('class') is None:
                    ing_object = child.text.strip().replace('\n', ' ')
                    req_list.append(ing_object)
        return req_list

    def get_serves(self):
        details_object = self.soup.find('ul', class_='recipe__details')
        if details_object:
            details_object = details_object.find_all('li')
            yields_object = None
            if len(details_object) == 3:
                yields_object = details_object[2]
            else:
                for p in details_object:
                    if 'Makes' in p.text or 'Serves' in p.text:
                        yields_object = p

            if yields_object:
                return yields_object.text

    def get_rating_out_100(self):
        ranking_object = self.soup.find(class_='recipe__rating')
        # Food52 rates recipes out of 5 stars based on comments.
        # Each star can either be 'rating__star' (20), 'rating__half-star' (10), 'rating__star--checked' (0).
        if ranking_object:
            # Loop over stars objects.
            ranking_out_100 = 0
            for star in ranking_object.div.find_all('div'):
                star_class = star.get('class')
                if star_class:
                    star_class = star_class[-1]
                    if star_class == 'rating__star':
                        ranking_out_100 += 20
                    elif star_class == 'rating__half-star':
                        ranking_out_100 += 10
                    elif star_class == 'rating__star--checked':
                        ranking_out_100 += 0
                    else:
                        # Be safe extraction team!
                        return

            return int(ranking_out_100)

    def get_steps(self):
        """ Scrape steps. """
        steps_object = self.soup.find(class_='recipe__list--steps')
        step_titles = steps_object.find_all(class_='recipe__list-subheading')
        
        parts = []
        step_list = []
        
        if steps_object:
            for i, part_tag in enumerate(steps_object.find_all('ol')):
                part = {}
                for step_tag in part_tag.find_all("li"):                
                    if step_tag.attrs['class'][0] == 'recipe__list-subheading':
                        part['method_name'] = f"Part {i+1}, {step_tag.text.strip()}"
                        part['steps'] = []
                    else:
                        step = Step()
                        text = step_tag.text.strip()
                        step.text = text
                        imgs = step_tag.find_all('img')
                        for img in imgs:
                            step.image.append(img['data-src'])
                            
                        if step_titles:
                            part['steps'].append(step)
                        else:
                            step_list.append(step)
                if step_titles:
                    parts.append(part)  
        
        print(parts)    
        if step_titles:
            return parts
        else:
            return step_list
