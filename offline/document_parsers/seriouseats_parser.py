from .abstract_parser import AbstractParser
from compiled_protobufs.document_pb2 import CustomDocument, Step


class SeriouseatsParser(AbstractParser):

    def get_title(self):
        """ Parse title. """
        title = self.soup.find(class_='heading__title')
        if title:
            return self.clean_text(title.text)

    def get_image(self):
        """ Parse image url. """
        image_object = self.soup.find('img', class_='primary-image')
        if image_object:
            return image_object['src']

        image_object = self.soup.find('img', class_='primary-image__image')
        if image_object:
            return image_object['src']

    def get_author(self):
        """ Parse author. """
        author = self.soup.find(id="mntl-byline__link_1-0")
        if author:
            return author.text

    def get_tags(self):
        """ Parse tags. """
        parent_object = self.soup.find(id='link-list_1-0')
        tag_list = []
        if parent_object:
            tag_objects = parent_object.find_all('a')
            for tag_object in tag_objects:
                tag = CustomDocument.Tag()
                tag.text = tag_object.text
                tag.url = tag_object['href']
                tag_list.append(tag)
        return tag_list

    def get_requirements(self):
        """ Parse requirements. """
        requirements_list = []
        # --- Ingredients ---
        ing_object = self.soup.find(id='ingredient-list_1-0')
        if ing_object:
            # Loop of ingredient objects to add full list.
            for child in ing_object.find_all('li'):
                requirements_list.append(child.text.strip())

        if len(requirements_list) == 0:
            ing_object = self.soup.find(id='structured-ingredients_1-0')
            if ing_object:
                # Loop of ingredient objects to add full list.
                for child in ing_object.find_all('li'):
                    requirements_list.append(child.text.strip())

        if len(requirements_list) == 0:
            return []

        # --- Equipment ---
        # Finding h2 tag of directions so that we can access next h2 tag which is special equipment
        steps_object = self.soup.find(id='structured-project__steps_1-0')
        if steps_object:
            steps_list = steps_object.find('ol')
            if steps_list:
                equip_object_header = steps_list.find_next('h2')
                if equip_object_header:
                    equip_object = equip_object_header.find_next_sibling('p')
                    if equip_object:
                        # Shard equipments list using comma.
                        for equipment in equip_object.text.split(','):
                            requirements_list.append(equipment.strip())

        return requirements_list

    def get_steps(self):
        """ Parse steps. """
        steps_object = self.soup.find(id='structured-project__steps_1-0')
        step_list = []
        if steps_object:
            # Loop over steps object to access associated text, images, or video.
            ol_object = steps_object.find('ol')
            if ol_object:
                for step_tag in ol_object.find_all("li"):
                    # Build Step object.
                    step = Step()
                    text = step_tag.p
                    if text:
                        step.text = text.text.strip()
                    else:
                        step.text = step_tag.text.strip()
                    imgs = step_tag.find_all('img')
                    for img in imgs:
                        if 'data-src' in str(img):
                            step.image.append(img['data-src'])
                        elif 'src' in str(img):
                            step.image.append(img['src'])
                    step_list.append(step)
        return step_list

    def get_date(self):
        """ Parse date. """
        text = self.soup.find(class_='comp mntl-updated-stamp__text mntl-text-block')
        if text:
            text = text.text
            # Remove 'Updated' from string.
            clean_text = " ".join(text.split(' ')[1:])
            # Parse text 'Aug. 31 2019' to date format YYYY-MM-DD.
            return self.parse_date(clean_text)

    def get_description(self):
        """ Parse descriptions. """
        description = ''
        subtitle = self.soup.find(class_='heading__subtitle')
        if subtitle:
            # Add subtitle.
            description += subtitle.text.strip()

        notes = self.soup.find(id='article__header--project_1-0')
        if notes:
            # Add notes
            description += notes.text.strip()
        return description

    def get_video(self):
        # TODO - find a way to work out lazy load for videos
        video_object = self.soup.find(id='mntl-sc-block-inlinevideo__video_1-0')
        if video_object:
            print('video found but lazy load')
            print(video_object)
            video_tag = video_object.find('video')
            if video_tag:
                return video_tag.get('src')

    def get_duration_minutes_total(self):
        """ Parse time it takes. """
        overall_time = 0
        prep_time = self.soup.find(id='active-time_1-0')
        if prep_time:
            prep_time = prep_time.text
            prep_time_min = self.parse_time(prep_time)
            overall_time += prep_time_min
        cooking_time = self.soup.find(class_='total-time')
        if cooking_time:
            cooking_time = cooking_time.text
            cooking_time_min = self.parse_time(cooking_time)
            overall_time += cooking_time_min

        return int(overall_time)

    def get_serves(self):
        """ Parse for how many people. """
        yields_object = self.soup.find(class_='recipe-yield')
        if yields_object:
            # --- Makes ---
            return yields_object.text.strip()
        else:
            # --- Serves ---
            serves_object = self.soup.find(class_='recipe-serving')
            if serves_object:
                return serves_object.text

    def get_rating_out_100(self):
        """ Parse rating. """
        ranking_object = self.soup.find(id='aggregate-star-rating__stars_1-0')
        if ranking_object:
            # Loop over stars objects.
            ranking_out_100 = 0
            for star in ranking_object.find_all('a'):
                star_class = star.get('class')
                if star_class:
                    star_class = star_class[0]
                    if star_class == 'active':
                        ranking_out_100 += 20
                    elif star_class == 'half':
                        ranking_out_100 += 10
                    elif star_class == 'inactive':
                        ranking_out_100 += 0
                    else:
                        # Be safe extraction team!
                        return

            return int(ranking_out_100)
