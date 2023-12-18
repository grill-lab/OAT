from .abstract_parser import AbstractParser
from document_pb2 import Step, CustomDocument
from utils import logger
from typing import List


def clean_text(text):
    text = text.replace('.\n', ". ")
    return text.replace('\n', '').strip(' .\n')


class WikihowParser(AbstractParser):

    def get_duration_minutes_total(self):
        pass

    def get_serves(self):
        pass

    def get_rating_out_100(self):
        pass

    def get_date(self):
        date_text = self.soup.find(class_='byline_info_link')
        if date_text:
            text = date_text.text
            # Remove 'Updated' from string.
            cleaned_text = " ".join(text.split(': ')[1:])
            # Parse text 'Aug. 31 2019' to date format YYYY-MM-DD.
            return self.parse_date(cleaned_text)

    def get_video(self):
        video_section = self.soup.find(id='video')
        if video_section:
            video_container = video_section.find(class_='embedvideo')
            if video_container:
                video_src = video_container.get('data-src')
                return video_src

    def get_validity(self, url):
        """ Check if valid url / taskgraph """
        return url[:23] == 'https://www.wikihow.com'

    def get_title(self):
        """ Parse title. """
        if self.soup.find(id='section_0'):
            return self.clean_text(self.soup.find(id='section_0').text)

    def get_image(self):
        """ Parse image url. """
        final_step_object = self.soup.find(class_='final_li')
        if not final_step_object:
            list_object = self.soup.find(class_='steps_list_2')
            if list_object:
                all_steps = list_object.find_all('li')
                if all_steps:
                    final_step_object = all_steps[len(all_steps) - 1]
        if final_step_object:
            image_object = final_step_object.find('img')
            if image_object:
                image_src = image_object.get('data-src')
                if not image_src:
                    image_src = image_object.get('src')
                if image_src is not None and image_src != '/skins/WikiHow/images/WH_logo.svg':
                    return image_src
            an_imgs = final_step_object.find("video", {"class": "m-video content-fill"})
            if an_imgs:
                src = an_imgs.get('data-giffirstsrc')
                if src:
                    return src
                src = an_imgs.get('data-poster')
                if src:
                    return src

    def get_author(self):
        """ Parse author. """
        author = self.soup.find(class_="coauthor_link")
        bad_authors = ['wikiHow Staff', 'Author Info']
        if author:
            if author.text in bad_authors:
                return ""
            return self.clean_text(author.text)

    def get_tags(self):
        """ Parse tags. """
        tags_list = []
        tag_objects_box = self.soup.find(class_='sp_box sp_fullbox')
        if tag_objects_box:
            tag_objects = tag_objects_box.find_all('a')
            for tag_object in tag_objects:
                tag = CustomDocument.Tag()
                tag.text = self.clean_text(tag_object.text)
                tag.url = tag_object['href']
                tags_list.append(tag)
        return tags_list

    def get_requirements(self):
        """ Parse requirements. """
        req_list = []

        ingr_object = self.soup.find(id='ingredients')
        if ingr_object:
            # Loop of ingredient objects to add full list.
            for child in ingr_object.find_all('li'):
                req_list.append(child.text.strip())

        tun_object = self.soup.find(id='thingsyoullneed')
        if tun_object:
            # Loop of ingredient objects to add full list.
            for child in tun_object.find_all('li'):
                req_list.append(child.text.strip())

        return req_list

    def __get_method_number(self) -> (int, list):
        """ Scrape how many methods the DIY article contains and save this number in DIYDocument.number_of_parallel_
        methods
        """
        steps_lists = self.soup.find_all(class_='steps')
        part_names = {}
        if len(steps_lists) > 0:
            header = steps_lists[0].find('h3')
            if header:
                for i in range(len(steps_lists)):
                    method_header = steps_lists[i].find('h3')
                    try:
                        method_headline = steps_lists[i].find("div", {"class": "headline_info"}).text
                    except:
                        method_headline = ''

                    if method_header is None and method_header:
                        logger.info('Failed parsing multiple parts/ methods')
                        return {}
                    else:
                        try:
                            if "Part" in method_header.text or "Part" in method_headline:
                                part_names[str(i)] = clean_text(f'Part {i + 1}: '
                                                                f'{method_header.find(class_="mw-headline").text}')
                            else:
                                part_names[str(i)] = clean_text(method_header.find(class_="mw-headline").text)
                        except:
                            return

            else:
                # DIY article has just one method, no parts
                return {}

        return part_names

    def get_steps(self) -> List[Step]:
        """ Parsing steps.

        Returns: a list of dictionaries containing the list of CustomDocument.Steps and a method name
            [ {"steps" : [STEP1, STEP2, ...], "method_name" : <method_name> }, ... ]

        """
        list_of_steps_list = self.soup.find_all('ol', class_='steps_list_2')
        method_names = self.__get_method_number()
        # logger.info(f'METHOD NUMBER: {method_names}')

        output_list = []
        if list_of_steps_list != []:
            # loop through all parts (which include an array of steps) of the article
            for i in range(len(list_of_steps_list)):
                part = list_of_steps_list[i]
                try:
                    output_list.append({'steps': self.__get_steps_list(part), 'method_name': method_names.get(str(i))})
                except:
                    return []
        return output_list

    @staticmethod
    def __get_steps_list(steps_list):
        """ Helper function to scrape all steps from list object """
        # Loop over steps object to access associated text, images, or video.

        steps = steps_list.find_all('li')
        count = 0
        output_list = []

        for step_tag in steps:
            if step_tag.get('id') is not None:
                count += 1
                # Build Step object.
                step = Step()
                step_object = step_tag.find(class_='step')
                if step_object:

                    # scrape bold step header
                    header = step_object.find('b')
                    if header:
                        header = clean_text(header.text)
                        step.headline = header

                    # filter out all videos/ script parts in text
                    for script in step_object.find_all('script'):
                        if "WH.video" in script.text:
                            try:
                                video_parts = str(script).split("getElementById('")
                                video_id = video_parts[1].split("'));</script>")[0]
                                video_obj = steps_list.find(id=video_id)
                                if video_obj:
                                    link = video_obj['data-src']
                                    step.video = f'https://www.wikihow.com/video{link}'
                            except:
                                pass
                        script.extract()

                        # filter out all misformatted divs
                        for div in step_object.find_all('div'):
                            div.extract()

                    # scrape all the remaining text after the bold step header
                    # filter out all references (e.g. [1])
                    for sup in step_object.find_all('sup'):
                        sup.extract()
                    for div in step_object.find_all('div'):
                        div.extract()

                    text = step_object.text
                    if step.headline in text:
                        text = text.strip(". \n")
                        text = text[len(step.headline):]

                    if isinstance(text, str):
                        cleaned_text = clean_text(text)
                        if len(cleaned_text) > 1:
                            if cleaned_text[-1] not in ["!", "?", ":"]:
                                cleaned_text += "."
                        step.text = cleaned_text

                # scrape all images found in the specific step section
                imgs = step_tag.find_all('img')
                for img in imgs:
                    src = img.get('data-src')
                    if src is not None and src != '/skins/WikiHow/images/WH_logo.svg':
                        step.image.append(src)

                an_imgs = step_tag.find_all("video", {"class": "m-video content-fill"})
                for animated_image in an_imgs:
                    src = animated_image.get('data-giffirstsrc')
                    if src:
                        step.image.append(src)
                        continue
                    src = animated_image.get('data-poster')
                    if src:
                        step.image.append(src)
                output_list.append(step)
        return output_list

    def get_description(self):
        """ Parse descriptions. """
        description = self.soup.find(id='mf-section-0')
        if description:
            # Add subtitle
            return self.clean_text(description.text)
