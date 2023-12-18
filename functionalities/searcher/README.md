# Task Searcher

Task Search is implemented in functionalities/searcher. 

## Abstract Searcher

All implemented searchers inherit from the `AbstractSearcher`. It contains an abstract method for retrieving tasks and a method for filtering out dangerous tasks after they are retrieved.

``` 
    @abstractmethod
    def search_taskgraph(self, query: SearchQuery) -> SearchResults:
        pass
```

### Input parameter: SearchQuery

A search object takes `SearchQuery` as a parameter:
- `SearchQuery` is a is an object responsible for storing information about the given query that needs to be processed for searching corresponding tasks
- its corresponding definition can be found in shared/protobufs/searcher.proto 
- it is intialized in functionalities/query_builder
- it can be extracted from the `Session` object

```   
SearchQuery {
    string text;            # text of the query (do not exactly understand the difference between this and last_utterance)
    int32 top_k;            # number of search results
    Session.Domain domain;  # either Cooking or DIY
    string last_utterance;  # string used in search
    bool headless;          # weather the device is with a screen or not
    string session_id;      # ID of the current session
    string turn_id;         # ID of the message in the session
}
```

### Output: SearchResults

`SearchResults` contains:
- a list of taskgraphs associated with the query
- output logs from the search

## Implemented Searchers:

- `ComposedSearcher` is responsible for loading and accessing all searches used in the system - for now we are only using SearcherPyserini to evaluate the query
- `SearcherPyserini` allows taskgraph retrieval in a multi-stage ranking architecture. It uses a Pyserni index to rank the documents based on a query.
- `FixedSearcher` allows fixing the search (for testing purposes)
- `RemoteSearcher` uses the search defined in the protobuffer for testing API connection

## Pyserini Index

The indexes and lookup files for search are located in shared/file_system. The sources from which these files are downloaded can be found in shared/setup.sh.










  
