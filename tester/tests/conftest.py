import os
import uuid

import pytest

from integration_tests.interaction import OATInteractionHelper


# see https://docs.pytest.org/en/7.1.x/example/simple.html#control-skipping-of-tests-according-to-command-line-option
def pytest_addoption(parser):
    """Adds custom arguments to pytest."""

    # pass --runslow to include tests marked as "slow"
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="Run potentially slow tests",
    )


def pytest_configure(config):
    """Add a new 'slow' value for marking potentially slow tests."""
    config.addinivalue_line("markers", "slow: marks test as (maybe) slow to run")


def pytest_collection_modifyitems(config, items):
    """Control inclusion/exclusion of slow tests."""

    # if the --runslow option was used, no need to modify the collection
    # of test items and can just return immediately
    if config.getoption("--runslow"):
        return

    # otherwise check for tests with the 'slow' marker and tell
    # pytest it should skip them in this run
    skip_slow = pytest.mark.skip(reason="use --runslow to include this test")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


@pytest.fixture
def new_session_obj():
    test_id = "test_" + str(uuid.uuid4())
    session = {
        "text": "",
        "id": test_id,
        "headless": False,
    }
    return session


@pytest.fixture
def interaction_obj():
    return OATInteractionHelper()


@pytest.fixture
def intent_parser_input_path() -> str:
    return os.environ.get("INTENT_PARSER_INPUT_PATH", "/shared/test_data/GRILL_intent_annotations.jsonl")


@pytest.fixture
def intent_parser_output_path() -> str:
    return os.environ.get("INTENT_PARSER_OUTPUT_PATH", "/shared/test_data/")


@pytest.fixture
def valid_downloads_path() -> str:
    return "/shared/test_data/valid_downloads.toml"


@pytest.fixture
def invalid_downloads_path() -> str:
    return "/shared/test_data/invalid_downloads.toml"


@pytest.fixture
def missing_values_downloads_path() -> str:
    return "/shared/test_data/missing_values_downloads.toml"
