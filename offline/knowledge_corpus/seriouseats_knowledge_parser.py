from .abstract_knowledge_parser import AbstractKnowledgeParser
from utils import logger, get_taskmap_id


class SeriouseatsKnowledgeParser(AbstractKnowledgeParser):
    """ Class to parse SeriousEats blog posts. Parses them into the KnowledgeDocument
        format defined in the offline.proto.
    """

    def __init__(self):
        pass

    @staticmethod
    def check_for_recipe(soup):
        return soup.find(id='structured-project__steps_1-0')

    def build_mentioned_recipe_ids(self, links):
        """ Helper function to check if a page contains a recipe, and if yes, then return the doc_id.
            Needs to be changed to retrieve the html of the link. For now just string matching URL
        """
        recipes = []
        for link in links:
            if link and "seriouseats" in link and "recipe" in link:
                recipes.append(self.get_docid(link))
        return recipes

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

    def get_author(self):
        """ Parse author. """
        author = self.soup.find(id="mntl-byline__link_1-0")
        if author is None:
            author = self.soup.find(class_='mntl-attribution__item-name')
        if author:
            return author.text

    def get_contents(self, url=None):
        """ Parse blog post contents. Here we differentiate between pages that are just blog posts and pages that
            have linked recipes.
        Returns:
              - a dictionary containing page information found, possible keys are linked_recipe_ids: [<doc_ids>],
                contents: list of strings containing passages on the webpage, and mentioned_links: [<string of urls>]
        """
        contents = []
        description = ''
        subtitle = self.soup.find(class_='heading__subtitle')
        if subtitle:
            # Add subtitle.
            description += subtitle.text.strip()

        contents.append(self.clean_text(description))

        if self.check_for_recipe(self.soup):
            # this page has a recipe
            article_container_object = self.soup.find(class_='article-intro')
            if article_container_object:
                for part in article_container_object.find_all(class_="mntl-sc-block-html"):
                    contents.append(f'{self.clean_text(part.text)}')

            return {"linked_recipe_ids": [self.get_docid(url)], "contents": contents}

        else:
            # this page is only a blog post
            article_container_object = self.soup.find(class_='structured-content')

            mentioned_links = []

            if article_container_object:

                subheaders = False
                for p in article_container_object.children:
                    if p.name == 'h3':
                        subheaders = True
                        break

                if subheaders:
                    so_far = ""
                    for part in article_container_object.children:
                        if part.name == 'h3':
                            if so_far != "":
                                contents.append(so_far)
                            so_far = f'{self.clean_text(part.text)}. '
                        elif part.name == 'p':
                            so_far += f'{self.clean_text(part.text)} '
                            if part.find('a'):
                                mentioned_links.append(part.find('a').get('href'))
                    if so_far != "":
                        contents.append(so_far)
                else:
                    for part in article_container_object.children:
                        if part.name == 'p':
                            contents.append(f'{self.clean_text(part.text)}')
            return {
                "contents": contents,
                "mentioned_tasks_ids": [link for link in mentioned_links if link is not None and  "seriouseats" in link],
                "linked_recipe_ids": self.build_mentioned_recipe_ids(mentioned_links)
            }

    def get_date(self):
        """ Parse date. """
        text = self.soup.find(class_='mntl-attribution__item-date')
        if text:
            text = text.text
            # Remove 'Updated' from string.
            clean_text = " ".join(text.split(' ')[1:])
            # Parse text 'Aug. 31 2019' to date format YYYY-MM-DD.
            return self.parse_date(clean_text)

