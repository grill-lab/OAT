from abstract_parser import AbstractParser
from compiled_protobufs.document_pb2 import Step, CustomDocument


class DoItYourselfParser(AbstractParser):
    def get_title(self):
        title_object = self.soup.find(id='title-header')
        if title_object:
            return title_object.text.replace('\n', '').strip()

    def get_date(self):
        pass

    def get_author(self):
        author_object = self.soup.find(class_='author-name')
        if author_object:
            author_name = author_object.find('a')
            if author_name:
                return author_name.text.replace('\n', '').strip()

    def get_description(self):
        content_object = self.soup.find(class_='diy-stry-body__content')
        if content_object:
            first_p = content_object.find('p')
            if first_p:
                return first_p.text.strip()

    def get_image(self):
        info_section = self.soup.find(class_='extend-info')
        if info_section:
            image = info_section.find_previous('img')
            if image:
                return image.get('data-src')

    def get_video(self):
        pass

    def get_duration_minutes_total(self):
        info_section = self.soup.find(class_='extend-info')
        if info_section:
            return self.parse_time(info_section.text)

    def get_tags(self):
        tags_list = self.soup.find_all(class_='tag-item')
        tags = []
        if tags_list:
            for item in tags_list:
                tag = CustomDocument.Tag()
                tag.text = item.text
                tags.append(tag)
        return tags

    def get_requirements(self):
        requirements_obj = self.soup.find(class_='tool-and-material__content')
        requirements_list = []
        if requirements_obj:
            for req in requirements_obj.div.div.find_all(class_='fa-check-square'):
                requirements_list.append(req.text)
        return requirements_list

    def get_serves(self):
        pass

    def get_rating_out_100(self):
        pass

    def get_steps(self):
        steps_headers = self.soup.find_all('h4')
        step_list = []
        if len(steps_headers) > 0:
            for step_header in steps_headers:
                step = Step()
                header = step_header.text
                step.headline = header
                text = step_header.next_sibling
                if text:
                    text = text.text
                    step.text = text
                step_list.append(step)
        return step_list
