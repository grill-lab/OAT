import os
import stream
import csv

from utils import logger, get_file_system
from offline_pb2 import HTMLDocument, CategoryDocument
from category_index.domain_classifier_categories import DomainClassifier

from urllib.parse import urlparse


class KnowledgeConstruction:
    def __init__(self, html_proto_path, knowledge_proto_path, parsers, tasks_that_require_scraping_path):
        self.html_proto_path = html_proto_path
        self.knowledge_proto_path = knowledge_proto_path
        self.parsers = parsers
        self.tasks_that_require_scraping_path = tasks_that_require_scraping_path
        self.new_taskmap_urls = set()
        self.domain_classifier = DomainClassifier()

    def run(self):
        self.load_knowledge_from_html()

    def __write_protobuf_list_to_file(self, path, protobuf_list, buffer_size=1000):
        stream.dump(path, *protobuf_list, buffer_size=buffer_size)

    def __read_protobuf_list_from_file(self, path, proto_message):
        return [d for d in stream.parse(path, proto_message)]
    
    def __store_task_urls(self, category: CategoryDocument):
        for subcategory in category.sub_categories:
            for candidate in subcategory.candidates:
                self.new_taskmap_urls.add(candidate.url)
    
    def __save_task_urls(self):
        processed_urls = []
        for url in self.new_taskmap_urls:
            parsed = urlparse(url)
            domain = parsed.netloc.split(".")[-2:]
            host = ".".join(domain)
            # follow common crawl's standard
            processed_urls.append([url, host, "2023-04-18 00:39:39.000","200","","","","",""])
        
        with open(self.tasks_that_require_scraping_path, 'w') as f:
            writer = csv.writer(f)
            for row in processed_urls:
                logger.info(f"Saved task url {row[0]} at {self.tasks_that_require_scraping_path}")
                writer.writerow(row)

    def parse_with_correct_parser(self, url, html):
        for parser_config in self.parsers:
            if parser_config["file_path"] in url:
                parser = parser_config["parser"]()
                new_doc = parser.parse(url, html)        
                if new_doc:
                    logger.info(f'Successfully parsed url: {url}')
                    if "seriouseats" not in url:
                        accepted_domains = ["DIYDomain", "UndefinedDomain", "CookingDomain"]
                        out = self.domain_classifier.classify_intent(new_doc.title)
                        if out.domain not in accepted_domains:
                            logger.info(f"Category classifier predicts: {out} for title {new_doc.title} -- FAILED")
                            return None
                        else:
                            logger.info(f"Category classifier predicts: {out} for title {new_doc.title} -- PASSED")
                return new_doc

    def load_knowledge_from_html(self):
        """ Method to read in html protos and convert them into KnowledgeDocument protos with the correct parser.
            Writes the new KnowledgeDocument out as a binary.
        """
        if not os.path.exists(self.knowledge_proto_path):
            os.makedirs(self.knowledge_proto_path, exist_ok=True)
        for domain in sorted(os.listdir(self.html_proto_path)):
            if any([p for p in self.parsers if p['file_path'] in domain]):
                logger.info(f'Looking at domain: {domain}')
                for batch in sorted(os.listdir(os.path.join(self.html_proto_path, domain))):
                    knowledge_protos = []
                    webpages = self.__read_protobuf_list_from_file(os.path.join(self.html_proto_path, domain, batch),
                                                                   HTMLDocument)
                    for webpage in webpages:
                        parsed_knowledge_doc = self.parse_with_correct_parser(webpage.url, webpage.html)
                        if parsed_knowledge_doc is not None:
                            knowledge_protos.append(parsed_knowledge_doc)
                            if self.tasks_that_require_scraping_path is not None:
                                self.__store_task_urls(parsed_knowledge_doc)
                            logger.info(f'{webpage.url} to knowledge doc')

                    filename = "knowledge_" + domain + "_" + batch.split("_")[-1]
                    if len(knowledge_protos) > 0:
                        self.__write_protobuf_list_to_file(os.path.join(self.knowledge_proto_path, filename),
                                                           knowledge_protos)
                    else:
                        logger.info(f'No parsable docs (len({len(webpages)})) in {domain}/{batch}')
            else:
                logger.info(f'Not parsable domain: {domain}')
        
        if self.tasks_that_require_scraping_path is not None:
            self.__save_task_urls()
