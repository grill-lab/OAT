from .abstract_taxonomy_builder import AbstractTaxonomyBuilder
from compiled_protobufs.offline_pb2 import CategoryDocument, SubCategory, Candidate
from utils import logger


class WikihowTaxonomyBuilder(AbstractTaxonomyBuilder):

    @staticmethod
    def get_title(soup):
        title_obj = soup.find('h1')
        if title_obj:
            return title_obj.text

        return ""

    def scrape_specific_category_page(self, sub_category: SubCategory):
        """ Given a sub-category page, we scrape candidates of the page
        Args:
            - sub_category: SubCategory which gets updated by this method
        """

        soup = self.get_soup(sub_category.url)
        if soup is None:
            return

        featured_grid = soup.find(id="cat_all")

        if featured_grid is None:
            return

        for item in featured_grid.find_all('a')[:3]:
            candidate: Candidate = Candidate()
            image = item.find('img')
            if image:
                candidate.image_url = "https://www.wikihow.com" + image["data-src"]
            title = item.find(class_='responsive_thumb_title').text
            candidate.title = title.strip('\n').replace('\n', " ")
            candidate.taskmap_id = self.get_docid(sub_category.url)
            candidate.url = item['href']

            sub_category.candidates.append(candidate)

    def locate_parent(self, soup, og_category: CategoryDocument):
        """ Since there is no taxonomy on the bottom of the page, we go up one level to get the category.
            This makes sure we don't lose the information original category page. We add the original
            category to the alternate queries.
        Args:
            - soup: original category page html
            - og_category: original category protobuf, will be updated in case the parent page has a taxonomy
        Returns:
            - sub_categories_section: if the parent page has a taxonomy grid, we return this for further processing
        """
        breadcrumb_section = soup.find(id="breadcrumb")
        if breadcrumb_section:
            crumbs = breadcrumb_section.find_all('li')
            if len(crumbs) > 1:
                parent = crumbs[-1]
                parent_link = parent.a

                if parent_link is not None:

                    og_category.alternate_queries.append(og_category.title)
                    og_category.title = parent.text
                    og_category.url = f"https://www.wikihow.com{parent_link['href']}"
                    parent_soup = self.get_soup(f"https://www.wikihow.com{parent_link['href']}")
                    if parent_soup is None:
                        return None

                    sub_categories_section = parent_soup.find(id="cat_sub_categories")
                    if sub_categories_section:
                        return sub_categories_section

        return None

    def scrape_category_overview_page(self, url, soup) -> CategoryDocument:
        """ Given the soup object of a page, we attempt populating a category document with metadata and
            subcategories, if available. If no subcategories are found, we process the parent category instead.

            We then scrape the category overview page for subcategories linked. For each sub-category,
            we scrape example candidates for the sub_category. This is the main functionality function.
        Args:
            - soup: html of the category page we are attempting to scrape
            - url: category page url
        Returns:
            - og_category: populated CategoryDocument with the information found on the WikiHow pages.
        """

        og_category: CategoryDocument = CategoryDocument()
        title = self.get_title(soup)

        if title == "" or "Category" not in url:
            # logger.info(f"FAILED: {url} not a Category")
            return

        og_category.url = url
        og_category.title = title
        og_category.cat_id = self.get_docid(url)

        # wikihow descriptions are rubbish
        # description = soup.find(id="cat_description")
        # if description:
        #     og_category.description = description.text.strip()

        sub_categories_section = soup.find(id="cat_sub_categories")

        if not sub_categories_section:
            # category is no overview page, can't scrape taxonomy
            parent_sub_categories_section = self.locate_parent(soup, og_category)
            if parent_sub_categories_section is not None:
                # went to parent
                sub_categories_section = parent_sub_categories_section
            else:
                # parent didn't work
                return None

        paginated = sub_categories_section.find_all("ul")

        for page in paginated:
            for sub_li in page.contents:
                if sub_li.name == "li":
                    cat = sub_li.div
                    if cat.has_attr("class"):
                        if "with_subsubcats" in cat["class"]:

                            # this sub_category has sub_categories - go down to furthest level of nesting
                            main_cat = cat.span.text

                            subs = cat.div.find_all('a')
                            for item in subs:
                                sub_category: SubCategory = SubCategory()
                                sub_category.title = item.text.strip()
                                sub_category.url = f'https://www.wikihow.com{item["href"]}'
                                sub_category.alternate_queries.append(main_cat.strip())

                            # linking all related mid-categories just in case
                            sub_cat = cat.find(class_='cat_link')
                            sub_cat_url = f"https://www.wikihow.com{sub_cat['href']}"
                            og_category.related_categories.append(self.get_docid(sub_cat_url))

                        elif "subcat_container" in cat["class"]:
                            # sub_category has no sub_categories, so can just link them
                            sub_category: SubCategory = SubCategory()
                            sub_category.title = cat.text.strip()
                            subs = cat.find("a")
                            sub_category.url = f'https://www.wikihow.com{subs["href"]}'

                            og_category.sub_categories.append(sub_category)

        for sub_cat in og_category.sub_categories:  # SubCategory
            self.scrape_specific_category_page(sub_cat)

        logger.info(f'Category {url}: success')

        return og_category

    def build_taxonomy(self, url, html=None) -> CategoryDocument:
        """
        Used to build the different categories available:
        Args:
            - urls (of the categories, e.g. {"url": https://www.wikihow.com/Category:Crafts, "name": "crafts"}
        Returns:
            - a CategoryDocument in the following format (if translated to a dictionary).
                For wikihow, it is populated for example as follows:
                {
                    'title': 'crafts',
                    'description': '',
                    'options_available': True,
                    'sub_categories': [
                        {'title': 'Animal Art and Craft',
                        'candidates': ['How to Make a Paper Butterfly',
                         'How to Make a Paper Cat',
                         'How to Make a Paper Dog',
                         'How to Make a Dog Out of Clay: A Step-by-Step Guide',
                         'How to Create Clay Animals',
                         'How to Make a Clay Bird'],
                        'thumbnail_url': ''
                        },
                       {'title': 'Basketry Wicker and Rattan',
                        'candidates': ['How to Make a Paper Basket'],
                        'thumbnail_url': ''},
                       {'title': 'Beading',
                        'candidates': ['How to Use Perler Beads',
                         'How to Make Orbeez: A Step-by-Step Guide',
                         'How to Make Beaded Curtains'],
                        'thumbnail_url': ''}
                    ]
                }, ...
            ]
        """

        soup = self.get_soup(url)
        if soup is None:
            return CategoryDocument()

        raw_cat = self.scrape_category_overview_page(url, soup)
        return raw_cat
