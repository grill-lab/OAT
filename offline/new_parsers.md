# Adding a new parser to the offline pipeline

This document contains a guide to implementing a new website parser for the offline pipeline. This can allow OAT to be configured to retrieve task or recipe information from sources that aren't included in the default configuration. 

## 1. Creating the new parser class

For the remainder of this document the parser will be assumed to be for `website.com` and called `WebsiteParser`. Substitute the name of the real website you want to add anywhere you see `website_parser` or `WebsiteParser` below (e.g. `allrecipes_parser` for an [allrecipes.com](https://www.allrecipes.com) parser).

Once you've decided which website you want to add to the pipeline, create a new file called `<name of website>_parser.py` in the `offline/document_parsers/` directory. 

Inside this file, create a new Python class subclassing `AbstractParser` and add empty placeholders for the abstract methods:

```python
from typing import Optional, List

from bs4 import Tag

from .abstract_parser import AbstractParser
from compiled_protobufs.document_pb2 import Step, CustomDocument


class WebsiteParser(AbstractParser):
    def get_title(self) -> Optional[str]:
        """Get the title of the task/recipe"""
        pass

    def get_date(self) -> Optional[str]:
        """Get the date the task/recipe was created/updated"""
        pass

    def get_author(self) -> Optional[str]:
        """Get the name of the author"""
        pass

    def get_description(self) -> Optional[str]:
        """Get any short description of the task/recipe"""
        pass

    def get_image(self) -> Optional[str]:
        """Get the URL of the main task/recipe image"""
        pass

    def get_video(self) -> Optional[str]:
        """Get video URL, if any"""
        pass

    def get_duration_minutes_total(self) -> Optional[int]:
        """Get the total time required for the task/recipe"""
        pass

    def get_tags(self) -> List[CustomDocument.Tag]:
        """Get any tags associated with the task/recipe"""
        return []

    def get_requirements(self) -> List[str]:
        """Get any requirements listed for the task/recipe (ingredients, tools, etc)"""
        return []

    def get_serves(self) -> Optional[str]:
        """Get the number of servings in a recipe"""
        pass

    def get_rating_out_100(self) -> Optional[int]:
        """Get task/recipe rating score on a 0-100 scale"""
        pass

    def get_steps(self) -> List[Step]:
        """Get the list of steps in the task/recipe"""
        return []
```

Each of these methods is intended to retrieve some piece of information from a webpage on the selected website. Many of the methods can simply return `None` if the information isn't available, but methods like `get_steps`, `get_requirements` and `get_tags` must return lists (even if the lists are empty). 

## 2. Implementing your parser

When you run the offline pipeline, HTML page data is retrieved from CommonCrawl. Next, based on the domain a parser is instantiated to extract the necessary data from the HTML. The details of this are handled in the `AbstractParser` class, so all you have to do in a subclass is implement the bodies of the placeholder methods so that they return the appropriate content from the page. 

The OAT parsers rely on the [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) HTML parsing module. When your parser is instantiated to parse a webpage, it will have access to a `BeautifulSoup` object via the `AbstractParser` base class. This will contain the parsed HTML, and you can then use the `BeautifulSoup` API to find and extract the relevant content. 

The easiest way to find the elements you need within the page structure is to simply open an example page in a browser and use the developer tools to inspect and filter the HTML. Once you have this information the next step is to compose `BeautifulSoup` API calls that retrieve the same elements. 

Here is an example from the `AllRecipesParser` class, which parses pages from [allrecipes.com](https://allrecipes.com):

```python
    def get_title(self) -> Optional[str]:
        """Get the title of the recipe"""
        # (when this method is called, self.soup will contain the parsed HTML already)
        # On this site, the recipe titles are inside an HTML element with the class
        # "article-heading", so we can simply search for that element and extract the
        # text content. 
        title_element = self.soup.find(class_="article-heading")
        if title_element is not None:
            # clean_text is defined by AbstractParser. it replaces newlines and tabs with spaces, 
            # and strips leading/trailing whitespace
            return self.clean_text(title_element.text)

```

Most of the methods to be implemented will probably be similar to this. However there are a few that are more complex:

### `get_steps`

This method must return a list of `Step` objects. These are protobuf objects defined in `shared/protobufs/document.proto`. An implementation of this method will normally be structured like this:

```python
def get_steps(self) -> List[Step]:
    step_elements = ... # get list of HTML elements containing steps

    parsed_steps = []
    for step_element in step_elements:
        step_text = ... # get text from the element
        step = Step()
        step.text = self.clean_text(step_text)
        # Steps may also have associated images/videos URLs:
        # step.video = ...
        # step.image = ...
        parsed_steps.append(step)

    return parsed_steps
```

### `get_date`

This method should return a string giving the date in `YYYY-MM-DD` format (`%Y-%m-%d` using Python's `datetime` format strings). You can optionally use the `parse_date` method of the `AbstractParser` class to convert a date to the correct format using `datetime`'s fuzzy parsing:

```python
original_date_string = "Updated on August 24, 2023"
parsed_date = self.parse_date(original_date_string)
print(parsed_date) # gives "2023-08-24"
```

### `get_requirements`

This method should return a list of strings where each entry is a requirement for starting/completing the task/recipe. In the case of a recipe this would be at least a list of ingredients. For a task it might be a list of tools or other equipment.

### `get_tags`

This method should return a list of `CustomDocument.Tag` objects. These are protobuf objects defined in `shared/protobufs/document.proto`. If you need to include tags, you can do something like this:

```python
def get_tags(self) -> List[CustomDocument.Tag]:
    html_tag_list = ... # extract a list of tags from the HTML

    doc_tags = []
    for tag in html_tag_list:
        doc_tag = CustomDocument.Tag()
        doc_tag.text = tag
        doc_tags.append(doc_tag)

    return doc_tags
```

## 3. Testing the parser

To make it easy to quickly test the parser during development, you can add a `__main__` method to your module and use the `offline` container to run it in the existing offline environment.

First, add a `__main__` that looks like this:

```python
if __name__ == "__main__":
    import urllib.request
    url = "..." # a URL for testing the parser on
    # retrieve the HTML content (this would normally be done by the CommonCrawl
    # component in the offline pipeline)
    html = urllib.request.urlopen(url).read().decode()
    # construct an instance of your parser and pass it the expected parameters
    WebsiteParser().parse(url, html)
```

Now you should be able to run this by executing the command:

`docker compose run -e PYTHONPATH=/shared:/shared/compiled_protobufs offline python3 -u -m document_parsers.website_parser`

This tells Docker to run the `offline` container with a different entrypoint, and also configures the `PYTHONPATH` environment variable to match what normally happens automatically. Note that you need to update the name of the parser to match the filename you used.

## 4. Integrating the parser

Once your parser is working, there are a few steps required to make the rest of the pipeline aware of it:

First, you need to create a parser definition in `offline/config.py`. Create a pair of new `dicts` matching the format of the existing set:

```python
website_config = {
    "file_path": "website",
    "parser": "WebsiteParser" # (remember to add an import for the parser class)
}

website_scraped_config = {
    "file_path": "website_scraped",
    "parser": "WebsiteParser",
}
```

These are used to define a mapping between a domain and the its corresponding parser class in different contexts.

Next, open `offline/document_parsers/mappings.py`. This defines 2 `dict`s that map domains to parsers and website names to domains. Add a new `import` statement for the new parser, and then insert a new entry into each of the dicts following the same format:

```python
...
from website_parser import WebsiteParser

document_parser_mappings = {
    ...,
    "website.com": WebsiteParser,
}

document_websites = {
    ...,
    "website": "website.com",
}
```

Finally, you need to decide how you want OAT to retrieve URLs from this website: sourcing the data from CommonCrawl, or scraping the content directly.

### 4.1 Using CommonCrawl

If you want to retrieve the data from CommonCrawl, see the documentation in [README.md](./README.md) that explains how to generate a CSV file in the appropriate format.

Once you have a suitable CSV file, you will need to edit `offline/config.py` again. The `offline_config` dict has a `steps` field that defines the list of pipeline components and the order they will be executed in. 

Find the entry for the `CommonCrawl` component (it should be first in the list), and append an entry to the `domains_to_run` list for the new domain, e.g.:

```python
    'domains_to_run': [wikihow_config, seriouseat_config, ..., website_config],
```

### 4.2 Using scraping

The other option is to perform direct scraping of URLs. OAT has an existing pipeline component to do this, but again it will require some configuration.

The component is called `Scraper`. Find the instance of this component in the `offline/config.py` file. Note that there are 2 instances; edit the one described as "Get HTML data via direct scraping". 

Update the `domains_to_run` and `scraper_csv_path` parameters:

```python
    # path to a CSV file which lists the URLs you want to scrape
    'scraper_csv_path': os.path.join(get_file_system(), 'offline/scraper_urls.csv'),
    # note that this should be website_scraped_config, not website_config!
    'domains_to_run': [website_scraped_config],
```
In some cases you may find the target site requires extra headers on each HTTP request, otherwise errors will be returned. If this happens, you can examine the headers your browser is sending using the browser console, and copy them into the `custom_headers` parameter of the `Scraper` component. For example, to add a user agent parameter:

```python
    'custom_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
    }
```

### 4.3 Common configuration

Regardless of how you retrieve the HTML data, you will also need to make some of the other OAT pipeline components aware of your new parser:

* In the definition of the `TaskgraphConstruction` component, add `website_config` to the `parsers` list
* In the same component, add `website_config` and `website_scraped_config` to the `parse_domains` list
* In the definition of the `AugmentationsIterator` component, add `website_config` and `website_scraped_config` to the `augment_domains` list

Now you can try running the pipeline with `docker compose run offline` and check if the URLs are retrieved successfully.

