import os
import pathlib

import tomli
import pytest
from dacite.exceptions import MissingValueError

from utils import Downloader



def test_download_https(valid_downloads_path: str, tmp_path: pathlib.Path) -> None:
    """
    Test a source which requires downloading from an HTTPS server.
    """

    d = Downloader(valid_downloads_path)
    # overwrite the actual downloads path with a temporary location
    d.config.base_path = str(tmp_path)

    d.download(["image_list_pickled", "image_url_lookup"])
    assert d.failed == 0
    assert d.succeeded == 2

    source_id = "example_source"

    # verify the file exists in the correct location
    output_path = d.get_path(source_id)
    assert os.path.isdir(output_path)
    filenames = d.list_contents(source_id)
    assert len(filenames) == 2  # folder + download marker

    # get the path to one of the files
    path = d.get_artefact_path("image_url_lookup")
    assert path is not None
    assert os.path.isfile(path)

def test_download_compressed(valid_downloads_path: str, tmp_path: pathlib.Path) -> None:
    """
    Test downloading a compressed file and auto-extracting it.
    """
    d = Downloader(valid_downloads_path)
    # overwrite the actual downloads path with a temporary location
    d.config.base_path = str(tmp_path)

    d.download(["image_list_pickled_compressed", "image_url_lookup_compressed"])
    assert d.failed == 0
    assert d.succeeded == 1 # only the zip file

    source_id = "compressed_source"

    # verify the file exists in the correct location
    output_path = d.get_path(source_id)
    assert os.path.isdir(output_path)
    filenames = d.list_contents(source_id)
    assert len(filenames) == 3  # zip + folder + download marker

    # get the path to one of the files
    path = d.get_artefact_path("image_url_lookup_compressed")
    assert path is not None
    assert os.path.isfile(path)

    # to test the part of the code that extracts compressed files when
    # artefacts are missing

    # remove the above file, then call download again which should
    # NOT download it again but should extract the .zip file again
    os.unlink(path)
    d.download(["image_url_lookup_compressed"])

    assert os.path.isfile(path)

def test_download_empty_local_path(valid_downloads_path: str, tmp_path: pathlib.Path) -> None:
    """
    Test that downloading works with an empty `local_path`.
    """

    d = Downloader(valid_downloads_path)
    # overwrite the actual downloads path with a temporary location
    d.config.base_path = str(tmp_path)
    d.config.sources[0].local_path = ""

    d.download(["image_list_pickled", "image_url_lookup"])
    assert d.failed == 0
    assert d.succeeded == 2

    source_id = "example_source"

    # verify the file exists in the correct location
    output_path = d.get_path(source_id)
    assert os.path.isdir(output_path)

    # get the path to one of the files
    path = d.get_artefact_path("image_url_lookup")
    assert path is not None
    assert os.path.isfile(path)


def test_download_disable_service(valid_downloads_path: str) -> None:
    """
    Test that disabling downloads for a service is correctly handled.
    """
    d = Downloader(valid_downloads_path)
    # disable the downloads for the whole service
    d.config.enabled = False

    assert d.download(["image_list_pickled", "image_url_lookup"]) is False  # returns False if no successful downloads
    assert d.failed == 0
    assert d.succeeded == 0


def test_download_set_force(valid_downloads_path: str, tmp_path: pathlib.Path) -> None:
    """
    Test re-downloading even if files exist
    """
    d = Downloader(valid_downloads_path)
    # overwrite the actual downloads path with a temporary location
    d.config.base_path = str(tmp_path)
    d.config.sources[0].force = True

    d.download(["image_list_pickled", "image_url_lookup"])
    assert d.failed == 0
    assert d.succeeded == 2

    source_id = "example_source"

    # verify the file exists in the correct location
    output_path = d.get_path(source_id)
    assert os.path.isdir(output_path)
    filenames = d.list_contents(source_id)
    assert len(filenames) == 2 # folder + download marker
    # create an empty file in the output path
    with open(os.path.join(output_path, "test"), "wb"):
        pass

    # now re-download the same files, and check that the files exist
    # again and that the test file has been removed
    d.download(["image_list_pickled", "image_url_lookup"])
    assert d.failed == 0
    assert d.succeeded == 2

    # verify the file exists in the correct location
    output_path = d.get_path(source_id)
    assert os.path.isdir(output_path)

    # get the path to one of the files
    path = d.get_artefact_path("image_url_lookup")
    assert path is not None
    assert os.path.isfile(path)

    filenames = d.list_contents(source_id)
    assert len(filenames) == 2  # folder + download marker

    assert not os.path.exists(os.path.join(output_path, "test"))


def test_download_skip_existing(valid_downloads_path: str, tmp_path: pathlib.Path) -> None:
    """
    Test that downloading is skipped if target files exist
    """
    d = Downloader(valid_downloads_path)
    # overwrite the actual downloads path with a temporary location
    d.config.base_path = str(tmp_path)

    d.download(["image_list_pickled", "image_url_lookup"])
    assert d.failed == 0
    assert d.succeeded == 2

    source_id = "example_source"

    # verify the file exists in the correct location
    output_path = d.get_path(source_id)
    assert os.path.isdir(output_path)
    filenames = d.list_contents(source_id)
    assert len(filenames) == 2  # folder + download marker

    # now re-download the same files, and check that the files exist
    # again and that the test file has been removed
    d.download(["image_list_pickled", "image_url_lookup"])
    assert d.failed == 0
    assert d.succeeded == 2

    # verify the file exists in the correct location
    output_path = d.get_path(source_id)
    assert os.path.isdir(output_path)

    # get the path to one of the files
    path = d.get_artefact_path("image_url_lookup")
    assert path is not None
    assert os.path.isfile(path)

    filenames = d.list_contents(source_id)
    assert len(filenames) == 2  # folder + download marker


def test_download_invalidconfig(invalid_downloads_path: str) -> None:
    """
    Test that supplying an invalid TOML config produces an exception.
    """
    with pytest.raises(tomli.TOMLDecodeError):
        Downloader(invalid_downloads_path)


def test_download_missingconfig() -> None:
    """
    Test that attempting to load a non-existent config file produces an exception.
    """
    with pytest.raises(FileNotFoundError):
        Downloader("missing_file.toml")


def test_download_missing_values(missing_values_downloads_path: str) -> None:
    """
    Test that attemping to load a config with missing mandatory values produces an exception.
    """
    with pytest.raises(MissingValueError):
        Downloader(missing_values_downloads_path)
