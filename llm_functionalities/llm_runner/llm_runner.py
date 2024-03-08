import os
import sys
import time
import concurrent.futures

from huggingface_hub import InferenceClient

from utils import logger
from compiled_protobufs.llm_pb2 import (
    ModelRequest,
    ModelResponse,
    ModelBatchRequest,
    ModelBatchResponse,
)


class LLMRunner:
    def __init__(self):
        endpoint_url = os.environ.get("INFERENCE_ENDPOINT_URL", None)
        if endpoint_url is None:
            logger.error("No INFERENCE_ENDPOINT_URL defined, container will exit")
            sys.exit(-1)

        if not endpoint_url.startswith("http://"):
            endpoint_url = f"http://{endpoint_url}"

        self.client = None
        retries = 0
        retry_limit = int(os.environ.get("TGI_CONNECTION_RETRY_LIMIT", 10))
        retry_delay = int(os.environ.get("TGI_CONNECTION_RETRY_DELAY", 10))
        logger.info(
            f"Connecting to TGI (max {retry_limit} connections, {retry_delay}s apart)"
        )

        # might have to wait for the TGI container to finish starting up, especially if it
        # needs to download model files first
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
            logger.error(
                f"LLMRunner failed to connect to the endpoint at {endpoint_url}"
            )
            sys.exit(-1)

    def _connect_to_endpoint(self, endpoint_url: str) -> InferenceClient:
        client = InferenceClient(model=endpoint_url, timeout=10.0)
        try:
            # creating the object doesn't appear to actually make a connection, so
            # try something that will fail if it can't connect
            client.text_generation(prompt="hello?", max_new_tokens=10)
        except Exception:
            return None
        return client

    def _check_connectivity(self) -> None:
        if self.client is None:
            raise Exception("llm_functionalities isn't connected to an endpoint!")

    def call_model(self, model_request: ModelRequest) -> ModelResponse:
        model_response: ModelResponse = ModelResponse()

        self._check_connectivity()

        try:
            response = self.client.text_generation(
                prompt=model_request.formatted_prompt,
                max_new_tokens=model_request.max_tokens,
            )
            logger.info(f"LLM response text: {response}")
            model_response.text = response

        except Exception as e:
            logger.warning(f"Call to inference endpoint failed: {e}")

        return model_response

    def batch_call_model(self, model_request: ModelBatchRequest) -> ModelBatchResponse:
        model_responses: ModelBatchResponse = ModelBatchResponse()

        self._check_connectivity()

        try:
            formatted_prompts = list(model_request.formatted_prompts)
            max_tokens = model_request.max_tokens
            params = [
                {"prompt": p, "max_new_tokens": max_tokens} for p in formatted_prompts
            ]

            logger.info(f"Submitting a batch of {len(params)} calls to TGI")
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(params)) as pool:
                results = pool.map(lambda p: self.client.text_generation(**p), params)

                for response in results:
                    logger.info(f"LLM response text: {response}")
                    model_responses.text.append(response)

        except Exception as e:
            logger.warning(f"Call to inference endpoint failed: {e}")

        return model_responses
