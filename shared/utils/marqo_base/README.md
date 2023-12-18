### Marqo base class

The base class allows the following functionality (only accessible within the marqo functionalities that implement the base class):
- `init()`: handles initialisation, including finding the marqo container environment URL, the default index settings, whether a GPU is available, the number of processes and the batch size that should be used.
- `check_if_index_exists()`: returns True if the given index name is in the indices in storage on the marqo-os container's volume. 

The Marqo functionality called is documented here: [Offical Marqo docs](https://docs.marqo.ai/)