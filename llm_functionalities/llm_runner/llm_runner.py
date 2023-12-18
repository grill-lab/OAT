
import torch

from transformers import AutoModelForCausalLM, AutoTokenizer
from torch.cuda import OutOfMemoryError

from utils import logger, Downloader
from compiled_protobufs.llm_pb2 import ModelRequest, ModelResponse, ModelBatchRequest, ModelBatchResponse


class LLMRunner:
    def __init__(self):
        if torch.cuda.is_available():
            artefact_id = "alpaca_llm"
            downloader = Downloader()
            downloader.download([artefact_id])
            model_name = downloader.get_artefact_path(artefact_id)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16,
                device_map="auto",
                max_memory={i: '24000MB' for i in range(torch.cuda.device_count())},
            )
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)

            self.batch_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.batch_tokenizer.padding_side = "left"
            self.batch_tokenizer.pad_token = self.batch_tokenizer.eos_token

            logger.info("Finished loading Alpaca model")
        else:
            logger.info('No GPU available, not loading LLM...')
            exit(1)

    def call_model(self, model_request: ModelRequest) -> ModelResponse:
        model_response: ModelResponse = ModelResponse()

        try:
            formatted_prompt = model_request.formatted_prompt
            max_tokens = model_request.max_tokens
            inputs = self.tokenizer(formatted_prompt, return_tensors="pt").to("cuda:0")
            outputs = self.model.generate(inputs=inputs.input_ids, max_new_tokens=max_tokens)
            response_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            model_response.text = str(response_text)

        except Exception as e:
            logger.info(f'Running LLM failed: {e}')

        return model_response

    def batch_call_model(self, model_request: ModelBatchRequest) -> ModelBatchResponse:
        model_responses: ModelBatchResponse = ModelBatchResponse()

        try:
            formatted_prompts = list(model_request.formatted_prompts)
            max_tokens = model_request.max_tokens

            encodings = self.batch_tokenizer(formatted_prompts, padding=True, return_tensors='pt').to("cuda:0")

            with torch.no_grad():
                generated_ids = self.model.generate(**encodings, max_new_tokens=max_tokens, do_sample=False)
            generated_texts = self.batch_tokenizer.batch_decode(generated_ids, skip_special_tokens=True)

            for text in generated_texts:
                model_responses.text.append(text)

        except OutOfMemoryError as e:
            logger.info(f'We ran out of GPU memory: {e}')
            torch.cuda.empty_cache()
            exit(1)
        
        return model_responses
