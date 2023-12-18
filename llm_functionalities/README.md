# LLM functionalities

This container contains the functionality required for the LLM to work.
You can find the code for the Alpaca-7B model based on LLaMA we currently use [here](https://github.com/tatsu-lab/stanford_alpaca).
This container automatically downloads the fine-tuned model from S3.

This container contains the [`llm_runner`](#llm-runner), which is called with prompts by other system components.
We have decided to host the LLM in another Docker container to ensure being able to allocate the required GPUs specifically.
The LLaMa model requires about ?? of GPU RAM to run.
We found that [AWS EC2 G5 instances](https://aws.amazon.com/ec2/instance-types/g5/) work best to run this model with a relatively high inference speed (depending on the number of tokens between 0.5 - 2.0 seconds).

### LLM runner
On spinning up the container, the LLM is loaded into GPU memory if a GPU is detected.
If not, the LLM is not loaded and the container quits gracefully.
It usually took about 3 minutes to load the model into memory.

By hosting the model in a separate Docker container, we are able to update prompts to the model from `functionalities` flexibly without waiting for the model to load into memory again.
On Kubernetes deployment, we could therefore restart the other containers without taking this container down.

Any module in the other Docker containers can either call the model with a batch request (`batch_call_model`) or a single request (`call_model`).
This is currently done by for example the following `functionalities`:
- [task description generation](./../functionalities/README.md#llm-description-generation)
- [proactive question generation](./../functionalities/README.md#llm-proactive-question-generation)
- [ingredient substitution](./../functionalities/README.md#llm-ingredient-substitution): step rewriting & replacement generation
- [step text improvement](./../functionalities/README.md#llm-summary-generation): If the step text is too short and we have linked details, we merge details and step text fluently.
- [chit chat](./../functionalities/README.md#llm-chit-chat): answer generation
- [QA](./../functionalities/README.md#qa): answer generation
- [Search execution classification](./../functionalities/README.md#execution-search-manager): used to decide whether the user would like to start a new search, or stay on the current task (since this is difficult for the NDP)

-------------
### Required models

If you want to define new models that the container has to load,
add the model name in `model_requirements.txt`, e.g. this how the file currently looks:
```text
alpaca_llm
```

The `download_required_artefacts.sh` will be run on startup of the docker
container and check if all models are available.
If not, and we are aws authenticated, we will download the required models.