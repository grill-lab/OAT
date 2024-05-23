import os
import sys
import time
from concurrent.futures import TimeoutError, ThreadPoolExecutor
from typing import Optional, Callable, Dict, Any

import dns.resolver
from huggingface_hub import InferenceClient

from utils import logger, Downloader
from compiled_protobufs.llm_pb2 import (
    ModelRequest,
    ModelResponse,
    ModelBatchRequest,
    ModelBatchResponse,
)

# default timeout for requests that don't set a timeout explicitly
# TODO: allow override by env var?
DEFAULT_TGI_TIMEOUT = 5
DEFAULT_TGI_TIMEOUT_MS = DEFAULT_TGI_TIMEOUT * 1000


class LLMRunner:
    def __init__(self):
        downloader = Downloader()
        logger.info(f"Found {len(downloader.sources)} enabled download sources, retrieving them...")
        # just download any defined sources
        downloader.download()

        endpoint_url = os.environ.get("INFERENCE_ENDPOINT_URL", None)
        if endpoint_url is None:
            logger.error("No INFERENCE_ENDPOINT_URL defined, container will exit")
            sys.exit(-1)

        # InferenceClient seems to require an http:// prefix for the URL
        if not endpoint_url.startswith("http://"):
            endpoint_url = f"http://{endpoint_url}"

        self.endpoint_url = endpoint_url
        self.client = None
        self._connect_to_endpoint()

    def _connect_to_endpoint(self) -> bool:
        """Attempt to make a connection to the configured TGI endpoint.

        Simply creating an InferenceClient object with the endpoint URL doesn't trigger
        a connection, so to force that to happen this just submits a small text_generation
        query. If the client object already exists it's taken to mean the connection
        has already been successfully established.

        Returns:
            True if a connection exists/was created, False otherwise.
        """

        # a client has been instantiated, assume everything is OK
        if self.client is not None:
            return True

        try:
            # First, need to check if we can actually resolve the TGI endpoint
            # hostname. If this isn't available, it will cause urllib3 and the Python
            # socket library to spend >10s waiting for a result. It seems to be hard
            # to do a time-limited host lookup using the stdlib,
            # but dnspython makes it easy (lifetime is the timeout parameter here):
            dns.resolver.resolve(self.endpoint_url[7:].split(":")[0], lifetime=1)

            # If the hostname is resolved, we then setup a longer timeout which
            # TGI will use internally when making HTTP requests via request.post() etc
            client = InferenceClient(model=self.endpoint_url, timeout=DEFAULT_TGI_TIMEOUT)

            # Finally, creating the object doesn't appear to actually make a connection,
            # so try something that requires a valid connection to succeed
            response = client.text_generation(prompt="hello?", max_new_tokens=10)
        except Exception as e:
            logger.warn(f"Failed to connect to TGI at {self.endpoint_url} ({e})")
            return False

        if len(response) == 0:
            logger.warn(f"Failed to connect to TGI at {self.endpoint_url} (timed out)")
            return False

        self.client = client
        return True

    def _call_with_timeout(self, timeout_ms: int, callable: Callable, params: Dict[str, Any]) -> str:
        """Call a TGI endpoint with a timeout applied.

        Since we want to avoid potentially lengthy LLM computations delaying the system's responses,
        we need to enforce a timeout on each TGI call. This method handles that using a
        ThreadPoolExecutor and a future object.

        Returns:
            The text response from the LLM, which will be empty if a timeout or other error
            occurs (str).
        """
        logger.info(f"call_with_timeout, timeout={timeout_ms}, params={params}")
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(callable, **params)
            try:
                response = future.result(timeout=timeout_ms / 1000)
                logger.info("TGI endpoint returned a response within timeout period")
                return response
            except TimeoutError as _:
                future.cancel()
                executor.shutdown(wait=False, cancel_futures=True)
                logger.warning(f"A call to the TGI endpoint has timed out after {timeout_ms} ms")
                return ""
            except Exception as e:
                future.cancel()
                executor.shutdown(wait=False, cancel_futures=True)
                logger.warning(f"A call to the TGI endpoint failed with an unexpected exception: {str(e)}")
                # assume this means a problem with the endpoint and connect again 
                # on a subsequent request
                self.client = None
                return ""

    def call_model(self, model_request: ModelRequest) -> ModelResponse:
        """Submit a single call to the LLM endpoint"""
        model_response: ModelResponse = ModelResponse()

        if not self._connect_to_endpoint():
            return model_response

        timeout_ms = DEFAULT_TGI_TIMEOUT_MS if model_request.timeout == 0 else model_request.timeout

        args = {
            "prompt": model_request.formatted_prompt,
            "max_new_tokens": model_request.max_tokens,
        }
        response = self._call_with_timeout(timeout_ms, self.client.text_generation, args)
        logger.info(f"LLM response text: {response}")
        model_response.text = response

        return model_response

    def batch_call_model(self, model_request: ModelBatchRequest) -> ModelBatchResponse:
        """Submit a batch of calls to the LLM endpoint"""
        model_responses: ModelBatchResponse = ModelBatchResponse()

        if not self._connect_to_endpoint():
            return model_responses

        timeout_ms = DEFAULT_TGI_TIMEOUT_MS if model_request.timeout == 0 else model_request.timeout

        formatted_prompts = list(model_request.formatted_prompts)
        max_tokens = model_request.max_tokens
        params = [{"prompt": p, "max_new_tokens": max_tokens} for p in formatted_prompts]

        logger.info(f"Submitting a batch of {len(params)} calls to TGI")
        # since TGI handles batching automatically in its backend, the recommended approach
        # seems to be simply submitting multiple requests in parallel as in the test fixtures:
        # https://github.com/huggingface/text-generation-inference/blob/main/integration-tests/conftest.py#L434
        with ThreadPoolExecutor(max_workers=len(params)) as pool:
            results = pool.map(lambda p: self._call_with_timeout(timeout_ms, self.client.text_generation, p), params)

            for response in results:
                logger.info(f"LLM response text: {response}")
                model_responses.text.append(response)

        return model_responses
