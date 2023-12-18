## Index building with Pyserini functionalities

We currently have two methods to build an index with Pyserini:
- **PyseriniBM25Builder**
- **PyseriniColbertBuilder**

If you want to create an index with one of those two methods, you need to implement either of those two classes.
This will require you to implement the `parse` and `build_doc` method.
The `parse` method defines on which part of the proto_message you are using should be parsed into the contents 
(the indexable, a.k.a. searchable text) for each doc in the final Pyserini index.
For example, for the normal task search index, we process each `TaskMap` in the following way:

```python
@staticmethod
def parse(proto_message):
    contents = ''
    contents += proto_message.title + '. '
    for requirement in proto_message.requirement_list:
        contents += requirement.name + ' '
    for tag in proto_message.tags:
        contents += tag + ' '
    contents += proto_message.description + ''
    for step in proto_message.steps:
        contents += step.response.speech_text + ' '

    return contents
```
The second function that needs to be implemented is `build_doc`.
This function takes the parsed contents and adds them into a dictionary.
For example, this is how `build_doc` is implemented for building the `TaskMap` index:
```python
from google.protobuf.json_format import MessageToDict

def build_doc(self, proto_message, include_proto):
    contents = self.parse(proto_message)
    if include_proto:
        return {
            "id": proto_message.taskmap_id,
            "contents": proto_message.taskmap_id,
            "recipe_document_json": MessageToDict(proto_message),
        }
    else:
        return {
            "id": proto_message.taskmap_id,
            "contents": contents,
        }
```

You can then implement the rest of your index builder in the following way:
```python
from index_builders import PyseriniBM25Builder

class VideoIndexBuilder(PyseriniBM25Builder):
    @staticmethod
    def parse(proto_message):
        # define your parsing behaviour here
    
    staticmethod
    def build_doc(self, proto_message, include_proto):
        # define your document building here

    def run(self):
        # in the run function, define where your json files should come from (usually temp)

        # build those docs if needed
        build_json_docs(input_dir=<WHERE DO YOUR PROTOS LIVE>, output_dir=<WHERE SHOULD THE JSONL LIVE>,
                        proto_message=<YOUR PROTO MESSAGE>, include_proto=True, 
                        build_doc_function=self.build_doc)
        # build the actual index
        self.build_index(input_dir=<WHERE SHOULD THE JSONL LIVE>, output_dir=self.index_dir)
```

### Helpful functions in `indexing_utils`:

1. `get_protobuf_list_messages(path, proto_message)`:
Given a path, retrieve a list of protocol buffer messages from binary fire

2. `write_protobuf_list_to_file(path, protobuf_list, buffer_size=10)`:
Given a path and a list of proto messages, write them to a binary file. """

3. `write_to_file`: Helper function for the function below

4. `write_doc_file_from_lucene_indexing(input_dir, output_dir, proto_message, build_doc_function: Callable,
                                        how='all', include_proto=False)`:
   Write json documents that represent proto messages into a folder.
   This is a helper function for the function below.

5. `build_json_docs(input_dir, output_dir, proto_message, build_doc_function: Callable,
                                        how='all', include_proto=False)`:
   The `input dir` defines where the protos should come from, 
   the `output_dir` defines where the jsonl should live that will be used for indexing.
   The `proto_message` will be whatever proto message type you are reading in from.
   `include_proto` defines whether the proto should be stored as an attribute in the index.
   The `build_doc_function` defines how the documents should be build and should be `self.build_doc`

