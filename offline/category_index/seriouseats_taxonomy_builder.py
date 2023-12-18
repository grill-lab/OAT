import os.path
import random
import json

from typing import List, Dict, Optional

from .abstract_taxonomy_builder import AbstractTaxonomyBuilder
from compiled_protobufs.offline_pb2 import CategoryDocument, SubCategory, Candidate

from utils import logger, get_file_system

TAXONOMY = {
    "course": ["Breakfast &amp; Brunch", "Mains", "Snacks &amp; Appetizers", "Salads", "Sides", "Desserts", "Drinks",
               "Condiments & Sauces"],
    "ingredient": ["Beans", "Beef", "Cheese", "Chicken", "Chocolate", "Duck", "Eggs", "Fats &amp; Oils", "Fruit",
                   "Goat", "Lamb", "Milk", "Noodles", "Nuts & Seeds", "Pastas", "Pork", "Rice &amp; Grains", "Sausages",
                   "Seafood", "Tofu", "Turkey", "Vegetables", "Other Meat &amp; Poultry"],
    "cuisine": ["African", "Asian", "Caribbean", "Central American", "Europe", "Middle Eastern", "North American",
                "Oceanic", "South American", "World Cuisines"]
}

FILTER_OUT_CATEGORIES = ["Food Science", "Food Industry", "Personal Essays", "Dining Out",
                         "Techniques", "Entertaining"]


def get_schema(soup):
    """ get schema.org json"""
    schema = soup.find_all('script', attrs={"type": "application/ld+json"})
    if schema:
        if len(schema) > 0:
            return json.loads(schema[0].string)


def get_tags(soup) -> List[Dict]:
    """ Parse tags. """
    parent_object = soup.find(id='link-list_1-0')
    tag_list = []
    if parent_object:
        tag_objects = parent_object.find_all('a')
        for tag_object in tag_objects:
            tag = {"text": tag_object.text, "url": tag_object['href']}
            tag_list.append(tag)
    return tag_list


class SeriousEatsTaxonomyBuilder(AbstractTaxonomyBuilder):

    def __init__(self):
        super().__init__()
        self.task_lookup = {}

    def check_for_recipe(self, soup, title=""):
        if soup.find(attrs={"id": 'structured-project__steps_1-0'}):
            # recipe page
            return True, title

        recipe_link = soup.find(attrs={"data-tracking-id": "featured-link-getrecipe"})
        if recipe_link is not None:
            # blog post with link to recipe
            if recipe_link.text != "Serious Eats":
                return True, recipe_link.text

        recipe_card = soup.find('a', class_='featured-recipe')
        if recipe_card is not None:
            # recipe card is found
            new_title = recipe_card.find(attrs={"class": "featured-recipe__title"})
            if new_title != "":
                return recipe_card['href'], new_title.text.strip('\n')

        recipe_inline = soup.find(class_="mntl-sc-block-subheading__text")
        if recipe_inline is not None:
            # inline recipes linked
            if "Get The Recipes" in recipe_inline.text:
                in_line_link = recipe_inline.find_next(attrs={"data-source": "inlineLink"})
                if in_line_link:
                    href = in_line_link['href']
                    link_soup = self.get_soup(href)
                    if link_soup is None:
                        return False, ""

                    is_recipe, new_title = self.check_for_recipe(link_soup, in_line_link.text)
                    if is_recipe:
                        return True, new_title

        recipe_guide = soup.find(attrs={"data-tracking-id": "featured-link-listlink"})
        if recipe_guide:
            text = recipe_guide.text.replace("Get the recipe for ", "")
            return recipe_guide['href'], text

        in_passage_link = soup.find_next(attrs={"data-source": "inlineLink"})
        if in_passage_link:
            if "Get the recipe" in recipe_inline.text:
                return in_passage_link['href'], recipe_inline.text.replace("Get the recipe for ", "")

        return False, ""

    def get_title(self, soup) -> str:
        """ Parse title. """

        recipe_blog_title = soup.find(class_='heading__title')
        if recipe_blog_title:
            return ""

        taxonomy_title = soup.find(id="mntl-taxonomysc-heading_1-0")

        if taxonomy_title:
            return self.clean_text(taxonomy_title.text)

        return ""

    def get_description(self, soup) -> str:
        descr_obj = soup.find(id="mntl-sc-block_1-0")
        if descr_obj:
            return self.clean_text(descr_obj.text)
        return ""

    def create_task_lookup(self, soup):
        """
        Scrape metadata for grid list item, e.g. an example task. Include the url, the taskmap_id as well as
        the image url
        """

        task_lookup = []

        schema = get_schema(soup)

        grid_items_text = soup.find_all(class_="card__title-text")
        grids_images = soup.find_all(class_="card__media")
        tags_content = soup.find_all(class_="card__content")
        schema_links = schema[0]["itemListElement"]

        if len(schema_links) == len(grid_items_text) and len(schema_links) == len(grids_images) \
                and len(tags_content) == len(grid_items_text):

            for i in range(len(schema_links)):
                task_url = schema_links[i]["url"]

                task_dict = {"title": grid_items_text[i].text,
                             "url": task_url,
                             "tag": tags_content[i]['data-tag']
                             }
                image = grids_images[i].find('img')
                if image is not None:
                    task_dict["image_url"] = image['data-src']
                else:
                    task_dict["image_url"] = ""

                task_lookup.append(task_dict)

            self.task_lookup = task_lookup
        else:
            logger.info("page is not consistent and can't be parsed")

    def get_task_meta(self, title) -> Optional[Dict]:
        """Retrieve the metadata for a task """
        for task in self.task_lookup:
            if task["title"] == title:
                return task
        return None

    def get_sub_categories(self, soup) -> tuple[List[Dict], List]:
        """ Method to get the seriouseats subcategories from category page
        Args:
            - soup presenting the html of the category page
        Returns:
            - sub_categorys: list of dictionaries representing the sub_category which are children of the main
                category linked on the seriouseats page
            - images: list of all urls and the representing task titles

        Probably needs to be refactored to not be using nested dicts but protobufs :(
        """
        example_dict = {}

        if self.task_lookup == {}:
            logger.info(f'No tasks found for this category')
            return [{}], []

        for task in self.task_lookup:

            # save category tag in grid item
            if task["title"] and task['tag'] is not None:
                if example_dict.get(task['tag']) is not None:
                    example_dict[task['tag']].append(task["title"])
                else:
                    example_dict[task['tag']] = [task["title"]]

        # count which tag has been used most
        counts = {}
        data_tags = [task['tag'] for task in self.task_lookup]
        for i in data_tags:
            counts[i] = counts.get(i, 0) + 1
        sorted_by_count = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)

        # appending the categories according to the amount of examples
        sub_categorys = []
        all_images = []

        selected_cat_no = 0

        for category, count in sorted_by_count:

            if selected_cat_no < 3:
                selected_cat_no += 1

                if category in FILTER_OUT_CATEGORIES:
                    continue

                cat_images = []

                first_cand_url = ""
                first_cand_title = ""
                for task in self.task_lookup:
                    if task["tag"] == category:
                        if first_cand_url == "" and first_cand_title == "":
                            first_cand_url = task['url']
                            first_cand_title = task['title']
                        cat_images.append(task['image_url'])

                if first_cand_url != "":
                    first_cand_soup = self.get_soup(first_cand_url)
                    if first_cand_soup is None:
                        return sub_categorys, all_images

                    is_recipe, new_title = self.check_for_recipe(first_cand_soup, title="")
                    if is_recipe:
                        if new_title != "":
                            candidates = [new_title for cand in example_dict[category] if cand == first_cand_title]
                        else:
                            candidates = example_dict[category]
                        sub_categorys.append(
                            {
                                "title": category,
                                "candidate_queries": candidates,
                                "thumbnail_url": random.choice(cat_images)
                            }
                        )
                        all_images.extend(cat_images)
                    else:
                        logger.info(f'Subcategory: {category} does not have recipes as candidates due to {first_cand_url}')

        return sub_categorys, all_images

    def build_taxonomy(self, url, html=None) -> CategoryDocument:
        """
        Given an url, build the taxonomy of a CategoryDocument for the system to use.
        Args:
            - url: url of the category
        Returns:
            - CategoryDocument: protobuf message encapsulating all content required for category options
        """
        soup = self.get_soup(url)
        if soup is None:
            return

        # filtering out links like https://www.seriouseats.com/
        if len(url.split("www.seriouseats.com")[1]) < 10:
            logger.info(f'skipping: {url}')
            return

        title = self.get_title(soup)

        if "Guide" in title:
            logger.info(f'Skipping {title} due to "Guide"')
        elif title != "":
            logger.info(f"Category found for title: {title}")

            category = CategoryDocument()

            self.create_task_lookup(soup)
            if self.task_lookup != {}:
                category.title = title
                category.url = url
                category.cat_id = self.get_docid(url+title)
                logger.info(f"Category title: {title}, Category id: {category.cat_id}, Category url {category.url}")
                tags = get_tags(soup)
                for tag in tags:
                    category.related_categories.append(self.get_docid(tag["url"]))
                category.description = self.get_description(soup)
                sub_cat_dict, images = self.get_sub_categories(soup)

                for cat in sub_cat_dict:
                    sub_category = SubCategory()

                    if cat["title"] in title.replace(" Recipes", ""):
                        logger.info(f'Renaming subcategory {cat["title"]} -> "Classics"')
                        sub_category.title = f'{cat["title"]} Classics'
                    elif cat["title"].strip('s') in title.replace(" Recipes", ""):
                        logger.info(f'Renaming subcategory {cat["title"]} -> "Classics"')
                        sub_category.title = f'{cat["title"].strip("s")} Classics'
                    else:
                        sub_category.title = cat["title"]
                    sub_category.thumbnail_url = cat["thumbnail_url"]

                    for cand in cat["candidate_queries"]:
                        candidate: Candidate = Candidate()
                        candidate.title = cand
                        task_meta = self.get_task_meta(cand)
                        if task_meta is not None:
                            candidate.url = task_meta["url"]
                            candidate.taskmap_id = self.get_docid(task_meta["url"])
                            candidate.image_url = task_meta["image_url"]

                        sub_category.candidates.append(candidate)
                    
                    # saving images found
                    images_path = os.path.join(get_file_system(), "offline/image_data")
                    if not os.path.isdir(images_path):
                        os.makedirs(images_path, exist_ok=True)

                    with open(os.path.join(images_path, f'{title.replace(" ", "_")}_images.jsonl'), "w") as json_file:
                        for img in images:
                            json.dump(img, json_file)
                            json_file.write('\n')

                    category.sub_categories.append(sub_category)

                if len(category.sub_categories) > 2:
                    logger.info(f'{category.title}: {[c.title for c in category.sub_categories]}')
                    return category
        return None

