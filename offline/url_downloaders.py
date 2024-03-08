import pandas as pd
import csv
import datetime
import os
import io
import gzip
import requests
import stream
import time
from typing import Any, Union
from abc import ABC, abstractmethod

from multiprocessing import Pool as ThreadPool
from tqdm.auto import tqdm

from utils import get_file_system, logger
from offline_pb2 import HTMLDocument


def format_time(elapsed: float) -> str:
    """
    Formats elapsed time in seconds as "hh:mm:ss".
    """
    return str(datetime.timedelta(seconds=int(round(elapsed))))


def write_protobuf_list_to_file(
    path: str, protobuf_list: list, buffer_size: int = 1000
) -> None:
    """
    Write a list of protos to a file, batching the writes in groups of <buffer_size> protos.
    """
    logger.info(f"Writing {len(protobuf_list)} protos to {path}")
    if len(protobuf_list) == 0:
        logger.warning(f"Refusing to write an empty list of protos to {path}")
    else:
        stream.dump(path, *protobuf_list, buffer_size=buffer_size)


def webpage_to_proto(webpage: dict) -> HTMLDocument:
    """
    Given webpage data in a dict, construct and return a populated HTMLDocument proto.
    """
    types = {
        "html": str,
        "url": str,
        "url_host_registered_domain": str,
        "fetch_time": str,
        "fetch_status": int,
        "warc_filename": str,
        "warc_record_offset": int,
        "warc_record_length": int,
        "warc_segment": float,
        "crawl": str,
    }

    html_proto = HTMLDocument()
    html_proto.html = webpage["html"]

    for key in webpage["metadata"].keys():
        setattr(html_proto, key, types[key](webpage["metadata"][key]))

    return html_proto


class DownloadBase(ABC):
    def run(self):
        self.failed_urls = []
        self.download()
        self.store_failed_urls()

    @abstractmethod
    def download(self) -> None:
        pass

    def store_failed_urls(self) -> None:
        """
        Write URLs in self.failed_urls into a file
        """

        # use the subclass name as part of the path
        stats_path = os.path.join(
            get_file_system(), "offline", "pipeline_stats", self.__class__.__name__
        )
        logger.info(f"Writing failed URLs to {stats_path}")

        os.makedirs(stats_path, exist_ok=True)

        with open(os.path.join(stats_path, "failed_urls.txt"), "w") as f:
            f.writelines(self.failed_urls)

    def get(
        self, url: str, headers: dict, timeout: float = 2.0
    ) -> Union[requests.Response, None]:
        """
        Wrapper for requests.get to handle errors.
        """
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            # this is False for return codes >= 400
            if not response.ok:
                # CommonCrawl servers currently return a lot of 503s, so don't show warnings
                # for these to avoid spamming log messages
                if response.status_code != 503:
                    logger.warning(f"GET on {url} returned code {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"GET failed on {url} with error {e}")
            return None

        return response


class Scraper(DownloadBase):
    def __init__(
        self,
        scraper_csv_path: str,
        html_proto_path: str,
        domains_to_run: dict,
        custom_headers: dict = {},
        protos_per_file: int = 1000,
    ) -> None:
        self.scraper_csv_path = scraper_csv_path
        self.html_proto_path = html_proto_path
        self.domains_to_run = domains_to_run
        self.custom_headers = custom_headers
        self.protos_per_file = protos_per_file

    def download(self) -> None:
        """
        Download URLs from the scraping list.
        """
        df = pd.read_csv(self.scraper_csv_path, header=None)

        os.makedirs(self.html_proto_path, exist_ok=True)

        logger.info(f"Scraper starting to run on {df.shape[0]} URLs")

        # TODO parallelize this? retries?
        for parser_conf in self.domains_to_run:
            parser_name = parser_conf["file_path"]
            parser_name_clean = parser_name.replace("_scraped", "")
            filtered_results_by_domain = list(
                filter(lambda row: parser_name_clean in row, df[df.columns[0]])
            )

            if len(filtered_results_by_domain) == 0:
                logger.warning(f"No entries found for domain {parser_name_clean}")
                continue

            parser_output_path = os.path.join(self.html_proto_path, parser_name)
            os.makedirs(parser_output_path, exist_ok=True)
            logger.debug(f"Created dir: {parser_output_path}")

            html_protos = []
            chunk = 0
            for i, url in sorted(enumerate(filtered_results_by_domain))[
                chunk * self.protos_per_file :
            ]:
                if i % self.protos_per_file == 0 and i > 0:
                    proto_path = os.path.join(parser_output_path, f"html_{chunk}.bin")
                    write_protobuf_list_to_file(proto_path, html_protos)
                    html_protos = []
                    chunk += 1

                logger.debug(f"Scraping {url}")
                resp = self.get(url, self.custom_headers)
                if resp is None:
                    logger.error(f"Failed to retrieve {url}")
                    self.failed_urls.append(url)
                    continue

                webpage = {
                    "metadata": {"url": url},
                    "html": resp.text,
                }
                html_protos.append(webpage_to_proto(webpage))

            os.makedirs(parser_output_path, exist_ok=True)

            proto_path = os.path.join(parser_output_path, f"html_{chunk}.bin")
            write_protobuf_list_to_file(proto_path, html_protos)
            logger.info(f"Scraper saved HTMLs at {proto_path}")

        logger.info(
            f"Scraper processed {df.shape[0]} URLs, {len(self.failed_urls)} failures"
        )


class CommonCrawl(DownloadBase):
    def __init__(
        self,
        common_crawl_path: str,
        html_proto_path: str,
        domains_to_run: list,
        protos_per_file: int = 1000,
        thread_pool_size: int = 5,
        retry_count: int = -1,
        retry_delay: float = 0.25,
    ):
        self.common_crawl_path = common_crawl_path
        self.html_proto_path = html_proto_path
        self.domains_to_run = domains_to_run
        self.protos_per_file = protos_per_file
        self.thread_pool_size = thread_pool_size
        self.retry_count = retry_count
        self.retry_delay = retry_delay

    def download(self) -> None:
        """
        Download CommonCrawl data.
        """
        df = pd.read_csv(self.common_crawl_path)
        rows = df.to_dict(orient="records")

        # if indefinite retries are enabled, display a message to explain that lack of
        # visible progress probably means we're getting a lot of HTTP 503s and it's
        # retrying silently instead of spamming the logs
        if self.retry_count == -1:
            logger.warning(
                "CommonCrawl downloads may appear to stall for long periods due to frequent "
                + "HTTP 503 errors. The downloader is currently configured to retry each download "
                + "indefinitely and they should eventually succeed given enough time."
            )

        results = []
        pool = ThreadPool(self.thread_pool_size)
        with tqdm(total=len(rows), desc="Downloading from CommonCrawl") as progress:
            for result in pool.imap(self.process_warc_query, rows):
                results.append(result)
                progress.update()

        pool.close()
        pool.join()

        os.makedirs(self.html_proto_path, exist_ok=True)

        for parser_conf in self.domains_to_run:
            counter = 1
            cc_html_path_chunk = ""
            chunk = 0
            webpage_protos = []

            parser_name = parser_conf["file_path"]
            parser_output_path = os.path.join(self.html_proto_path, parser_name)
            os.makedirs(parser_output_path, exist_ok=True)
            logger.info(f"Created dir: {parser_output_path}")

            filtered_results_by_domain = filter(
                lambda row: row is not None and parser_name in row["metadata"]["url"],
                results,
            )

            for webpage in filtered_results_by_domain:
                cc_html_path_chunk = os.path.join(
                    parser_output_path, f"html_{chunk}.bin"
                )
                if webpage is not None:
                    webpage_proto = webpage_to_proto(webpage)
                    webpage_protos.append(webpage_proto)
                    counter += 1
                    if counter % self.protos_per_file == 0:
                        chunk += 1
                        write_protobuf_list_to_file(cc_html_path_chunk, webpage_protos)
                        webpage_protos = []

            if counter % self.protos_per_file != 0 and len(webpage_protos) > 0:
                write_protobuf_list_to_file(cc_html_path_chunk, webpage_protos)

        logger.info(
            f"CommonCrawl processed {len(rows)} URLs, {len(self.failed_urls)} failures"
        )

    def process_warc_query(self, metadata: dict) -> Union[dict, None]:
        """
        Extract required attributes from a CSV row and attempt to download the data.
        """
        try:
            metadata["fetch_time"] = str(metadata["fetch_time"])
            request = {
                "offset": metadata["warc_record_offset"],
                "length": metadata["warc_record_length"],
                "filename": metadata["warc_filename"],
            }
            html = self.download_single_result(request)["html"]
            webpage = {"metadata": metadata, "html": html}
            return webpage
        except Exception as e:
            logger.warning(f"process_warc_query caught exception: {e}")
            self.failed_urls.append(metadata["url"])

        return None

    def download_single_result(self, result: dict) -> dict:
        """
        Downloads HTML for single search result.

        Args:
            result: Common Crawl Index search result from the search function.

        Returns:
            The provided result, extended by the corresponding HTML String.
        """

        offset, length = int(result["offset"]), int(result["length"])
        offset_end = offset + length - 1
        url = "https://data.commoncrawl.org/{filename}".format(
            filename=result["filename"]
        )
        headers = {"Range": f"bytes={offset}-{offset_end}"}

        retries = 0
        # if retry_count is -1 this will retry indefinitely
        while retries < self.retry_count or self.retry_count == -1:
            response = self.get(url, headers)
            if response is not None:
                break

            retries += 1
            if self.retry_count != -1 and retries >= self.retry_count:
                # this will be handled in process_warc_query, where it will add the URL to the failed list
                raise Exception(f"Retries exceeded for {url}!")

            time.sleep(self.retry_delay)

        unzipped_file = gzip.GzipFile(fileobj=io.BytesIO(response.content))
        raw_data: bytes = unzipped_file.read()
        try:
            data: str = raw_data.decode("utf-8")
        except UnicodeDecodeError:
            print(f"Warning: Could not extract file downloaded from {url}")
            data = ""

        result["html"] = ""

        if len(data) > 0:
            data_parts = data.strip().split("\r\n\r\n", 2)
            result["html"] = data_parts[2] if len(data_parts) == 3 else ""

        return result
