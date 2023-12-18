from index_builders import KnowledgeConstruction


class TaxonomyBuildRunner:

    def __init__(self, html_proto_path, tasks_that_require_scraping_path,
                 knowledge_proto_path, parsers, objects_index_dir, index_builder):
        self.html_proto_path = html_proto_path
        self.tasks_that_require_scraping_path = tasks_that_require_scraping_path
        self.knowledge_proto_path = knowledge_proto_path
        self.parsers = parsers
        self.objects_index_dir = objects_index_dir
        self.index_builder = index_builder

    def run(self):
        # run knowledge corpus builder to parse docs with parsers
        parser_runner = KnowledgeConstruction(self.html_proto_path, self.knowledge_proto_path,
                                              self.parsers, self.tasks_that_require_scraping_path)
        parser_runner.run()

        # run build json docs & run indexing
        index_builder = self.index_builder(proto_path=self.knowledge_proto_path,
                                           objects_index_dir=self.objects_index_dir)
        index_builder.run()
