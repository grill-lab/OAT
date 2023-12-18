from .abstract_parser import AbstractParser
from compiled_protobufs.document_pb2 import Step


class FoodAndWineParser(AbstractParser):

    def get_title(self):
        """ Parse title. """
        title = self.soup.find(class_='intro article-info')
        if title:
            return self.clean_text(title.text)

    def get_image(self):
        """ Parse image url. """
        media_section = self.soup.find(class_='primary-media-section')
        if media_section:
            image_object = media_section.find('img')
            if image_object:
                return image_object['src']

    def get_author(self):
        pass
        """ Parse author. """
        author = self.soup.find(class_="author-name")
        if author:
            return author.text.strip('\n').strip()

    def get_tags(self):
        return []

    def get_requirements(self):
        """ Parse requirements. """
        # --- Ingredients ---
        req_list = []
        ing_object = self.soup.find(class_='ingredients-section')
        if ing_object:
            # Loop of ingredient objects to add full list.
            for child in ing_object.find_all('li'):
                req_list.append(child.text.strip())
        return req_list

    def get_steps(self):
        step_list = []
        """ Parse steps. """
        steps_object = self.soup.find(class_='instructions-section')
        if steps_object:
            # Loop over steps object to access associated text, images, or video.
            for step_tag in steps_object.find_all("li"):
                # Build Step object.
                step = Step()
                text = step_tag.p
                if text:
                    step.text = text.text.strip()
                else:
                    step.text = step_tag.text.strip()
                imgs = step_tag.find_all('img')
                for img in imgs:
                    step.image.append(img['data-src'])
                step_list.append(step)
        return step_list

    def get_date(self):
        pass

    def get_url(self, url):
        self.doc.url = url

    def get_description(self):
        """ Parse descriptions. """
        description = ''
        summary = self.soup.find(class_='recipe-summary')
        if summary:
            # Add subtitle.
            description += summary.text.strip()

        return description

    def get_video(self):
        pass

    def get_duration_minutes_total(self):
        """ Parse time it takes. """
        overall_time = 0
        details_section = self.soup.find(class_='recipe-info-section')
        if details_section:
            time_section = details_section.find(class_='two-subcol-content-wrapper')
            if time_section:
                for time_tag in time_section.find_all(class_='recipe-meta-item-body'):
                    overall_time += int(self.parse_time(time_tag.text))
        return overall_time

    def get_serves(self):
        """ Parse for how many people. """
        details_section = self.soup.find(class_='recipe-info-section')
        if details_section:
            detail_parts = details_section.find_all(class_='two-subcol-content-wrapper')
            if detail_parts != [] and len(detail_parts) > 1:
                return detail_parts[1].text.replace('\n', '').strip().replace('  ', '')

    def get_rating_out_100(self):
        pass
