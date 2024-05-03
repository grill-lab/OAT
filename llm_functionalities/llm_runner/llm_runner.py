import os
import sys
import time
from concurrent.futures import TimeoutError, ThreadPoolExecutor
from typing import Optional, Callable, Dict, Any

from huggingface_hub import InferenceClient

from utils import logger
from compiled_protobufs.llm_pb2 import (
    ModelRequest,
    ModelResponse,
    ModelBatchRequest,
    ModelBatchResponse,
)

# default timeout for requests that don't set a timeout explicitly
# TODO: allow override by env var?
DEFAULT_TGI_TIMEOUT_MS = 5000


class LLMRunner:
    def __init__(self):
        endpoint_url = os.environ.get("INFERENCE_ENDPOINT_URL", None)
        if endpoint_url is None:
            logger.error("No INFERENCE_ENDPOINT_URL defined, container will exit")
            sys.exit(-1)

        # InferenceClient seems to require an http:// prefix for the URL
        if not endpoint_url.startswith("http://"):
            endpoint_url = f"http://{endpoint_url}"

        self.client = None
        retries = 0
        retry_limit = int(os.environ.get("TGI_CONNECTION_RETRY_LIMIT", 10))
        retry_delay = int(os.environ.get("TGI_CONNECTION_RETRY_DELAY", 10))
        logger.info(f"Connecting to TGI (max {retry_limit} connections, {retry_delay}s apart)")

        # might have to wait for the TGI container to finish starting up, especially if it
        # needs to download model files first. the two TGI_CONNECTION_RETRY_* env vars
        # determine how long we'll wait for this to happen.
        while retries < retry_limit:
            client = self._connect_to_endpoint(endpoint_url)
            if client is None:
                logger.info(f"LLMRunner retrying connection to {endpoint_url}")
                time.sleep(retry_delay)
                retries += 1
            else:
                logger.info("LLMRunner connected to endpoint!")
                self.client = client
                break

        if self.client is None:
            logger.error(f"LLMRunner failed to connect to the endpoint at {endpoint_url}")
            sys.exit(-1)

    def _connect_to_endpoint(self, endpoint_url: str) -> Optional[InferenceClient]:
        """Attempt to make a connection to the configured TGI endpoint.

        Simply creating an InferenceClient object with the endpoint URL doesn't trigger
        a connection, so to force that to happen this just submits a small text_generation
        query.

        Returns:
            None if the connection failed, otherwise an InferenceClient object
        """
        client = InferenceClient(model=endpoint_url, timeout=10.0)
        try:
            # creating the object doesn't appear to actually make a connection, so
            # try something that will fail if it can't connect
            client.text_generation(prompt="hello?", max_new_tokens=10)
        except Exception:
            return None
        return client

    def _check_connectivity(self) -> bool:
        """Test if we have a connected InferenceClient"""
        if self.client is None:
            logger.error("!!! llm_functionalities isn't connected to an endpoint!")
            return False

        return True

    def _call_with_timeout(self, timeout_ms: int, callable: Callable, params: Dict[str, Any]) -> str:
        """Call a TGI endpoint with a timeout applied.

        Since we want to avoid potentially lengthy LLM computations delaying the system's responses,
        we need to enforce a timeout on each TGI call. This method handles that through a
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
                logger.warning(f"A call to the TGI endpoint has timed out after {timeout_ms} ms")
                return ""
            except Exception as e:
                future.cancel()
                logger.warning(f"A call to the TGI endpoint failed with an unexpected exception: {str(e)}")
                return ""

    def call_model(self, model_request: ModelRequest) -> ModelResponse:
        """Perform a single call to the LLM endpoint"""
        model_response: ModelResponse = ModelResponse()

        if not self._check_connectivity():
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

        if not self._check_connectivity():
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
