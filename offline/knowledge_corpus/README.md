## Knowledge corpus construction

### Running the knowledge corpus building:
Steps:
1. Set `CommonCrawl`, `KnowledgeConstruction` and `KnowledgeIndexBuilder` to True in `offline/config.py`
    - if you want to run on GPU, add the GPU discovery to the `docker-compose.yaml` (see *Running on GPU* below)
2. Spin up Marqo: ``docker-compose up --build marqo`` (see *Running Marqo* below)
3. Run the offline pipeline: ``docker-compose up --build offline``

### Description of components

This directory contains two parts:
1. Parsing blog posts from their html
2. Build the knowledge corpus

The Knowledge corpus is meant to contain files in the following format (defined in `shared/protobufs/offline.proto`):
```
message KnowledgeDocument{
    // Unique identifier for each TaskMap within the TaskMap index.
    string knowledge_id = 1;
    // Title of task being completed.
    string title = 2;
    // Date (format: YYYY-MM-DD) when the TaskMap input data was created (for example when published online).
    string date = 3;
    // URL that the TaskMap input data was extracted.
    string source_url = 4;
    repeated string contents = 5;
    string author = 6;
}
```

### Parsing
For the parsing, we can currently parse the following blog posts:
- seriouseats (for example: https://www.seriouseats.com/food-lab-how-to-grill-steak-cuts-of-steak)

The parsing can be configured in `offline/config.py`. The runner takes the following arguments: 'html_proto_path', 'knowledge_proto_path' and 'parsers'.
In parsers, you can define what blog posts you would like to process, for example `seriouseats_knowledge_config` defines that we would like to parse seriouseats blog posts.

The `KnowledgeConstruction` takes whatever HTML protos it can find from `shared/file_system/offline/htmls` and processes the parsed blog posts into `KnowledgeDocument` protos.
They are saved as a binary dump in `shared/file_system/offline/knowledge`.

### Indexing with Pyserini
In `knowledge_corpus/knowledge_corpus_builder.py`, we run the building of the knowledge corpus.
We take the `KnowledgeDocument` proto binaries in `shared/file_system/offline/knowledge` and pass them into our Pyserini indexing tools.

We switched to indexing with Pyserini, as the Marqo functiontionality was not
able to run on Kubernetes.
To index with Pyserini, we have tools created in `index_builders` which the `PyseriniKnowledgeIndexer` can implement.
This allows for standardised indexing between different indexes being created.

*Running with GPU*
If you would like to use GPU to index, you need to ensure the Docker Compose configuration for the `offline` service includes a GPU section like this:
```
    deploy:
      resources:
        reservations:
          devices:
          - driver: nvidia
            count: 1 # set to 0 to run without a GPU
            capabilities: [gpu]
```

This will allow the containers to detect the GPU that the system has.

The `KnowledgeIndexBuilder` takes in 4 arguments: 'knowledge_proto_path', 'index_name', 'batch_size', 'processes'.

The current default settings are what worked best on a [GPU EC2 instance](https://aws.amazon.com/releasenotes/aws-deep-learning-ami-gpu-pytorch-1-13-ubuntu-20-04/).
