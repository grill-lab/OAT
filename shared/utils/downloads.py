import os
from dataclasses import dataclass, field
from typing import Callable, List, Optional
import shutil

import dacite
import requests
import tomli
import tqdm

from utils import logger


# Dataclasses used to parse TOML with dacite
#
# https://gitlab.com/-/snippets/2335713
@dataclass
class DownloadSource:
    id: str
    urls: List[List[str]]
    artefacts: List[List[str]] = field(default_factory=list)
    base_path: str = ""
    local_path: str = ""
    enabled: bool = True
    force: bool = False
    decompress: bool = True


@dataclass
class DownloadConfig:
    name: str
    base_path: str
    sources: List[DownloadSource]
    http_timeout: float = 5.0
    enabled: bool = True


class Downloader:
    def __init__(self, downloads_file: str = "downloads.toml") -> None:
        logger.info(f"Downloader parsing download information from {downloads_file}")

        self.config = dacite.from_dict(
            data_class=DownloadConfig, data=tomli.load(open(downloads_file, "rb"))
        )
        self._sources = {s.id: s for s in self.config.sources}
        self._prefix = f"Downloader({self.config.name})"
        self._failed_downloads = 0
        self._successful_downloads = 0
        self._artefacts = {
            s.id: {v[0]: v[1] for v in s.artefacts} for s in self.config.sources
        }

    @property
    def sources(self) -> dict[str, DownloadSource]:
        """
        Dict mapping source IDs to DownloadSource instances.
        """
        return self._sources

    @property
    def succeeded(self) -> int:
        """
        Return number of successful downloads
        """
        return self._successful_downloads

    @property
    def failed(self) -> int:
        """
        Return number of failed downloads
        """
        return self._failed_downloads

    def download(
        self, artefact_ids: List[str] = [], filter_urls: Optional[Callable] = None
    ) -> bool:
        """
        Download all defined sources, or a subset based on requested artefacts.

        If artefact_ids is an empty list, this method will download all sources defined in the
        configuration file. If one or more artefact IDs are supplied, then downloading is only
        performed for the source(s) containing those IDs.

        filter_urls can be a Callable which takes a URL and returns True/False. This will be
        applied to the list of URLs for each source being processed, so you can use it to
        remove certain URLs from the list to be downloaded if necessary.
        """

        self._failed_downloads = 0
        self._successful_downloads = 0

        if not self.config.enabled:
            logger.warning(f"{self._prefix}: service downloads are disabled in config!")
            return False

        # if artefact_ids were requested, only want to download the sources which contain those IDs
        logger.info(f"{self._prefix}: # artefact_ids = {len(artefact_ids)}")
        if len(artefact_ids) > 0:
            sources_to_download = {}
            for aid in artefact_ids:
                source = self.get_artefact_source(aid)
                if source.id not in sources_to_download:
                    sources_to_download[source.id] = source
                logger.info(
                    f"{self._prefix}: adding source {source.id} for artefact {aid}"
                )
        else:
            sources_to_download = {source.id: source for source in self.config.sources}

        logger.info(
            f"{self._prefix}: processing {len(sources_to_download)}/{len(self.config.sources)} sources"
        )

        for i, source in enumerate(sources_to_download.values()):
            if len(source.urls) == 0:
                raise Exception(
                    f"Source {source.id} in service {self.config.name} has no URLs!"
                )

            urls = source.urls
            if filter_urls is not None:
                urls = list(filter(filter_urls, urls))
                logger.info(
                    f"{self._prefix}: Filtered URLs from {len(source.urls)} to {len(urls)}"
                )

            logger.info(
                f"{self._prefix}: source {i+1}/{len(sources_to_download)}, # URLs = {len(urls)}"
            )

            source_failed = 0
            for url, local_name in urls:
                result = self._download(url, local_name, source)
                if not result:
                    self._failed_downloads += 1
                    source_failed += 1
                else:
                    self._successful_downloads += 1

            if source_failed == 0:
                self._post_download(source)

        logger.info(
            f"{self._prefix}: {self._successful_downloads} downloads completed, {self._failed_downloads} downloads failed"
        )
        return self._successful_downloads > 0

    def _download(self, url: str, local_name: str, source: DownloadSource) -> bool:
        if not self._pre_download(source):
            return True

        if url.lower().startswith("http"):
            return self._download_http(url, local_name, source)

        raise Exception(f"Unsupported URL scheme: {url}")

    def _marker_for_source(self, source: DownloadSource) -> str:
        """
        Return a download marker filename for the source.
        """
        return f".{source.id}.downloaded"

    def _do_local_files_exist(self, source: DownloadSource) -> bool:
        """
        Check if the source files seem to have been downloaded already.

        This will check:
            - does the base output path exist?
            - does the .<source id>.downloaded file exist?
            - does the base_path/local_path path exist for each URL?

        If any of these fail, return False, otherwise True.
        """

        path = self.get_path(source.id)

        logger.info(
            f"{self._prefix}: checking if local files exist at '{path}' for {source.id}"
        )
        if not os.path.isdir(path):
            logger.info(
                f"{self._prefix}: no local files found at '{path}' for {source.id}"
            )
            return False

        if not os.path.exists(os.path.join(path, self._marker_for_source(source))):
            logger.info(
                f"{self._prefix}: path '{path}' exists but no download marker for {source.id}"
            )
            return False

        for _, local_name in source.urls:
            if not os.path.exists(os.path.join(path, local_name)):
                logger.info(
                    f"{self._prefix}: path '{os.path.join(path, local_name)} not found for {source.id}"
                )
                return False

        logger.info(f"{self._prefix}: local files found at '{path}' for {source.id}")
        return True

    def _remove_local_files(self, path: str) -> bool:
        """
        Remove a set of local files at the indicated path.
        """
        try:
            logger.info(f"{self._prefix}: removing path '{path}'")
            shutil.rmtree(path, ignore_errors=False)
        except Exception as e:
            logger.warning(
                f"{self._prefix}: errors encountered when removing path '{path}' ({e})"
            )
            return False

        return True

    def _pre_download(self, source: DownloadSource) -> bool:
        """
        Called just before downloading to check for existing local files.

        Returns a bool indicating if the download process should continue (True) or be
        skipped (False).
        """
        if self._do_local_files_exist(source):
            if not source.force:
                logger.info(
                    f"{self._prefix}: local files exist, but force=false so skipping download"
                )
                # local files seem to be downloaded already and config indicates not to re-download
                return False
            else:
                # local files seem to be downloaded already but config indicates we should remove and reacquire
                logger.info(
                    f"{self._prefix}: local files exist, force=true so will delete and reacquire"
                )
                self._remove_local_files(self.get_path(source.id))
                return True

        # local files don't exist
        logger.info(f"{self._prefix}: local files don't exist, will download")
        return True

    def _can_decompress(self, filename: str) -> bool:
        """
        Returns True if a filename has a supported compressed extension.
        """
        fl = filename.lower()

        for ext in [".tar.bz2", ".tar.gz", ".bz2", ".gz", ".zip"]:
            if fl.endswith(ext):
                return True

        return False

    def _decompress(self, source: DownloadSource, filename: str) -> bool:
        """
        Decompress a bz2/gz/zip file into the same directory as the original.
        """
        extract_to = os.path.split(filename)[0]

        logger.info(f"{self._prefix}: extracting {filename} from {source.id}")
        try:
            os.makedirs(extract_to, exist_ok=True)
            shutil.unpack_archive(filename, extract_dir=extract_to)
        except Exception as e:
            logger.warning(
                f"{self._prefix}: failed to extract {filename} from {source.id}: {e}"
            )
            return False

        return True

    def _post_download(self, source: DownloadSource) -> bool:
        """
        Called just after a set of downloads successfully completes.
        """

        # if there are compressed files in the list of URLs, check if there are any
        # artefact files that don't exist locally. if any don't exist, assume that they
        # are contained in the compressed files and extract them 
        if source.decompress:
            local_files_missing = False
            for id, _ in source.artefacts:
                if not os.path.exists(self.get_artefact_path(id)):
                    local_files_missing = True
                    break

            if local_files_missing:
                logger.info(f"{self._prefix}: missing artefact(s) and compressed downloads detected, extracting archives")

                local_names = [
                    self.get_local_name(source.id, i) for i in range(len(source.urls))
                ]
                local_names = list(filter(self._can_decompress, local_names))

                if len(local_names) > 0:
                    logger.info(
                        f"{self._prefix}: found {len(local_names)} decompressible local paths in source {source.id}"
                    )

                    for local_name in local_names:
                        self._decompress(
                            source, os.path.join(self.get_path(source.id), local_name)
                        )

        # create an empty file in the output folder called ".<name of source>.downloaded" as an
        # indicator that the source has been downloaded (this is only done if all URLs were
        # downloaded successfully)
        with open(
            os.path.join(self.get_path(source.id), self._marker_for_source(source)),
            "wb",
        ):
            pass

        return True

    def _download_http(self, url: str, local_name: str, source: DownloadSource) -> bool:
        """
        Download a file over HTTP(S).
        """

        download_path = os.path.join(self.get_path(source.id), local_name)
        # create the output directory structure in case it doesn't already exist
        logger.info(f"Creating download path: {os.path.dirname(download_path)}")
        os.makedirs(os.path.dirname(download_path), exist_ok=True)
        logger.info(f'{self._prefix}: downloading "{url}" => {download_path}')

        try:
            response = requests.get(url, timeout=self.config.http_timeout, stream=True)
            # this is False for return codes >= 400
            if not response.ok:
                logger.warning(f"GET on {url} returned code {response.status_code}")
                return False

            # https://gist.github.com/yanqd0/c13ed29e29432e3cf3e7c38467f42f51
            file_size = int(response.headers.get("content-length", 0))

            with open(download_path, "wb") as f, tqdm.tqdm(
                desc=local_name,
                total=file_size,
                unit="iB",
                unit_scale=True,
                unit_divisor=1024,
            ) as progress:
                for chunk in response.iter_content(chunk_size=4096):
                    progress.update(f.write(chunk))
        except Exception as e:
            logger.warning(f"GET failed on {url} with error {e}")
            return False

        return True

    def _check_valid_source(self, source_id: str) -> None:
        """
        Raise an exception if an invalid source ID is supplied.
        """
        if source_id not in self._sources:
            raise Exception(
                f"Invalid source ID '{source_id}' not found in DownloadConfig"
            )

    def get_path(self, source_id: str) -> str:
        """
        Given a source ID, return the path to the directory containing its files.
        """
        self._check_valid_source(source_id)

        source = self._sources[source_id]

        # check for overridden base_path
        if len(source.base_path) > 0:
            return os.path.abspath(os.path.join(source.base_path, source.local_path))

        return os.path.abspath(os.path.join(self.config.base_path, source.local_path))

    def list_contents(self, source_id: str) -> List[str]:
        """
        Wrapper for calling os.listdir(<path to source source_id>)
        """
        return os.listdir(self.get_path(source_id))

    def get_url(self, source_id: str, n: int) -> str:
        """
        Get the nth URL for a source
        """
        self._check_valid_source(source_id)

        return self._sources[source_id].urls[n][0]

    def get_local_name(self, source_id: str, n: int) -> str:
        """
        Get the local name for the nth URL for a source
        """
        self._check_valid_source(source_id)

        return self._sources[source_id].urls[n][1]

    def get_artefact_source(self, name: str) -> DownloadSource:
        """
        Given an artefact ID, return the source that contains it
        """
        for source_id, artefacts in self._artefacts.items():
            if name in artefacts:
                return self._sources[source_id]

        raise Exception(
            f"artefact {name} was not found in the Downloader configuration"
        )

    def get_artefact_path(self, name: str) -> str:
        """
        Given an artefact ID, return its downloaded path.
        """
        for source_id, artefacts in self._artefacts.items():
            if name in artefacts:
                path = os.path.join(self.get_path(source_id), artefacts[name])
                logger.info(
                    f"{self._prefix}: found artefact {name} in source {source_id} with path {path}"
                )
                return path

        raise Exception(
            f"artefact {name} was not found in the Downloader configuration"
        )
