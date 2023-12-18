from index_builders.general_knowledge_construction import KnowledgeConstruction


class KnowledgeCorpusBuilder:
    def __init__(self, html_proto_path, parsers, index_builder, knowledge_proto_path,
                 knowledge_index_search_dir, knowledge_index_objects_dir):
        self.html_proto_path = html_proto_path
        self.parsers = parsers
        self.index_builder = index_builder
        self.knowledge_proto_path = knowledge_proto_path
        self.index_search_dir = knowledge_index_search_dir
        self.index_objects_dir = knowledge_index_objects_dir

    def run(self):
        # running knowledge parsing
        parser_runner = KnowledgeConstruction(self.html_proto_path, self.knowledge_proto_path, self.parsers, None)
        parser_runner.run()

        # running building of the index
        pyserini_index_builder = self.index_builder(self.knowledge_proto_path, self.index_search_dir, self.index_objects_dir)
        pyserini_index_builder.run()
