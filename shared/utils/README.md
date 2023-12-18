# OAT utilities package

The `shared.utils` Python package contains a collection of utility methods that are used by multiple services in the system. The `shared` folder is typically mounted to each of the OAT deployment containers using `/shared` as a mountpoint, and the `PYTHONPATH` environment variable is updated to allow imports to work as intended. 

This file gives a brief overview of each of the modules in the package. For more detailed information, see the docstrings in the individual source files or use the HTML documentation. 

## Modules

### utils.general

Helper methods that don't fit anywhere else. 

### utils.session

A collection of methods for interacting with `Session` protobuf objects and some of the other objects it contains. Also methods for examining and modifying intents in the current session. These are used extensively by the policies in the `orchestrator` service. 

### utils.logging

Sets up logging for OAT services, attempting to parse configuration settings from `shared/log_config.yaml`. It also looks for environment variables `LOGGING_LEVEL` and `CONTAINER_NAME` to construct the name of the new logger. 

### utils.nlp

Contains an implementation of the Jaccard Similarity Index.

### utils.search

Contains a simple dict of theme recommendations, e.g. "dinner" is mapped to "thai green curry", "salad" to "chicken caesar salad".

### utils.policies

Helper methods for policies in the `orchestrator` service. Currently this just contains a single method used to populate the `OutputSource` field of the `OutputInteraction` produced by policies. 

### utils.scripts

Some helper scripts for extracting objects from a database (sessions, search logs). See the [README](scripts/README.md).

### utils.aws

Contains some classes and methods for managing DynamoDB instances. These are currently only used by `external_functionalities/database/dynamo_db.py`.

There is also a `timeit` module which implements a `@timeit` function decorator to measure execution times. It has its own [README](aws/readme.md).

### utils.constants

Contains definitions of some constant values used by some of the services. The main content here at the moment is in `utils.constants.prompts.all_prompts`, where most of the hardcoded system responses to various situations are defined (e.g. responses to financial/medical/legal queries).
