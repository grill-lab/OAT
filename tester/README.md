# OAT Tester

The `tester` container contains the dependencies necessary for running the OAT unit and integration tests. The tests themselves can be found under `tester/tests`. By default the container will run only unit tests, excluding those marked as "slow". 

See below for more information and how to configure the set of tests that the container will run. 

## General information

### Environment

The `tester` directory will be mounted to the container at `/source` and the default `WORKDIR` is `/source`. This allows relative paths to be used, e.g. `tests/unit_tests`. 

The `shared` directory is also mounted to the container at `/shared`. 

### Passing arguments to pytest

The container's entrypoint is defined to be the pytest executable, so you can use any valid combination of [pytest arguments](https://docs.pytest.org/en/7.0.x/how-to/usage.html) to control the selection of tests to run or modify pytest's behaviour. See below for examples. 

### Custom options

There are currently some pytest options that can be passed to the container:
 * `--runslow` will include tests that are marked as being slow to run (these are excluded by default)

If you need to mark a test as "slow", use the `pytest.mark.slow` decorator:

```python
@pytest.mark.slow
def some_slow_test():
    ...
```

## Running tests

To run the unit tests (excluding any marked as slow), you can just start the container without any arguments:

```bash
# equivalent to pytest tests/unit_tests
docker compose run tester
```

Other examples:

```bash
# running all unit tests (including "slow" ones)
docker compose run tester --runslow tests/unit_tests

# running only integration tests...
docker compose run tester tests/integration_tests

# ... including "slow" tests
docker compose run tester --runslow tests/integration_tests

# run both unit and integration tests
docker compose run tester tests/

# run a subset of tests from the full collection
docker compose run tester -k test_personality
```

### Intent parser test

This test loads some data from a path inside the `shared` directory and saves a file to a different location in the same directory. The default values for these are defined in `tester/tests/conftest.py`. They can be overridden on the command line if needed:

```bash
# override the default output path
docker compose run -e INTENT_PARSER_OUTPUT_PATH=/shared/intent_parser_output tester
# override the default input path
docker compose run -e INTENT_PARSER_INPUT_PATH=/shared/intent_parser_input tester
```
